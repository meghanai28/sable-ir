import os
import tarfile
import stat


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    # Phase 0: Establish trust boundary
    try:
        os.makedirs(dest_path, exist_ok=True)
        if not os.path.isdir(dest_path):
            return False
        trust_boundary = os.path.realpath(dest_path)
        if not trust_boundary.endswith(os.sep):
            trust_boundary += os.sep
    except (OSError, ValueError):
        return False

    # Phase 1: Validation pass
    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
    except (tarfile.TarError, OSError, IOError):
        return False

    validated_members = {}  # name -> member
    validated_paths = {}    # name -> normalized path
    regular_file_members = set()  # set of normalized paths
    symlink_targets = {}    # name -> raw target string
    hardlink_targets = {}   # name -> normalized target path

    def sanitize_member_name(name):
        # Strip leading absolute path indicators
        while name.startswith('/') or name.startswith('\\'):
            name = name[1:]
        # Strip Windows drive letters
        if len(name) >= 2 and name[1] == ':':
            name = name[2:]
            while name.startswith('/') or name.startswith('\\'):
                name = name[1:]
        return name

    def normalize_and_check(candidate_path, allow_exact_boundary=False):
        try:
            normalized = os.path.normpath(candidate_path)
            # Resolve any remaining .. components that might escape
            # os.path.normpath handles .. but we need to verify boundary
            if normalized == trust_boundary.rstrip(os.sep):
                return normalized if allow_exact_boundary else None
            if not normalized.startswith(trust_boundary):
                return None
            # Ensure it's not something like /dest/../outside via exact prefix check
            # The startswith check with trailing separator handles this
            return normalized
        except (ValueError, OSError):
            return None

    def get_candidate_path(name):
        sanitized = sanitize_member_name(name)
        if not sanitized:
            # Empty name would map to trust boundary, only valid for directories
            return trust_boundary.rstrip(os.sep)
        candidate = os.path.join(trust_boundary.rstrip(os.sep), sanitized)
        return candidate

    for member in members:
        # Check for path traversal in member name
        if '..' in member.name.split('/') or '..' in member.name.split('\\'):
            return False

        candidate = get_candidate_path(member.name)
        normalized = normalize_and_check(candidate, allow_exact_boundary=(member.isdir() or member.issym() or member.islnk()))

        if normalized is None:
            return False

        # Empty sanitized name for non-directory is invalid
        sanitized = sanitize_member_name(member.name)
        if not sanitized and not member.isdir():
            return False

        validated_members[member.name] = member
        validated_paths[member.name] = normalized

        # Check file type
        if member.isreg():
            regular_file_members.add(normalized)
        elif member.isdir():
            pass  # Directories are fine
        elif member.issym():
            # Validate symlink target
            raw_target = member.linkname
            if raw_target is None:
                return False

            if os.path.isabs(raw_target):
                # Absolute target: normalize directly
                # Strip leading markers for absolute targets too
                abs_target = raw_target
                while abs_target.startswith('/') or abs_target.startswith('\\'):
                    abs_target = abs_target[1:]
                if len(abs_target) >= 2 and abs_target[1] == ':':
                    abs_target = abs_target[2:]
                    while abs_target.startswith('/') or abs_target.startswith('\\'):
                        abs_target = abs_target[1:]

                if abs_target:
                    resolved = os.path.normpath(os.path.join(trust_boundary.rstrip(os.sep), abs_target))
                else:
                    resolved = trust_boundary.rstrip(os.sep)
            else:
                # Relative target: resolve from parent of member
                parent_dir = os.path.dirname(normalized)
                resolved = os.path.normpath(os.path.join(parent_dir, raw_target))

            # Check resolved path is within trust boundary
            if resolved == trust_boundary.rstrip(os.sep):
                # Symlink to trust boundary itself is allowed
                pass
            elif not resolved.startswith(trust_boundary):
                return False

            symlink_targets[member.name] = raw_target

        elif member.islnk():
            # Hard link: validate target
            target_name = member.linkname
            if target_name is None:
                return False

            target_sanitized = sanitize_member_name(target_name)
            target_candidate = os.path.join(trust_boundary.rstrip(os.sep), target_sanitized) if target_sanitized else trust_boundary.rstrip(os.sep)
            target_normalized = normalize_and_check(target_candidate, allow_exact_boundary=False)

            if target_normalized is None:
                return False

            # Target must be a regular file member in this archive
            # We need to check if the target name corresponds to a validated regular file
            # The link target name might reference a member by its archive name
            target_member = validated_members.get(target_name)
            # Also check if it's a member we haven't processed yet, or check by path
            # Actually, we need to map: the hardlink target name should match an archive member name
            found_target = False
            for mname, mpath in validated_paths.items():
                if mpath == target_normalized and mname in validated_members:
                    if validated_members[mname].isreg():
                        found_target = True
                        break

            # Also check if target_name directly names a member
            if not found_target and target_name in validated_members:
                if validated_members[target_name].isreg():
                    found_target = True
                    target_normalized = validated_paths[target_name]

            if not found_target:
                return False

            hardlink_targets[member.name] = target_normalized

        else:
            # Reject device nodes, FIFOs, and other non-standard types
            return False

    # Phase 2: Extraction
    try:
        # Open dest_path directory fd for safe relative operations
        dest_fd = os.open(dest_path, os.O_RDONLY | os.O_DIRECTORY)
    except (OSError, IOError):
        return False

    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            # Track which paths we've successfully created
            created_paths = set()

            for member in members:
                if member.name not in validated_members:
                    return False

                normalized_path = validated_paths[member.name]
                member_obj = validated_members[member.name]

                # Guard against TOCTOU: verify parent directories are real directories
                parent = normalized_path
                while parent != trust_boundary.rstrip(os.sep):
                    parent = os.path.dirname(parent)
                    if parent == trust_boundary.rstrip(os.sep):
                        break
                    if parent in created_paths:
                        # We created this, but it could have been replaced
                        # Stat to verify it's still a directory
                        try:
                            st = os.stat(parent)
                            if not stat.S_ISDIR(st.st_mode):
                                return False
                        except (OSError, IOError):
                            return False
                    else:
                        # Pre-existing, verify it's a real directory
                        try:
                            st = os.stat(parent)
                            if not stat.S_ISDIR(st.st_mode):
                                return False
                        except (OSError, IOError):
                            return False

                if member_obj.isdir():
                    try:
                        os.makedirs(normalized_path, exist_ok=True)
                        created_paths.add(normalized_path)
                    except (OSError, IOError):
                        return False

                elif member_obj.isreg():
                    try:
                        # Ensure parent directory exists
                        parent_dir = os.path.dirname(normalized_path)
                        os.makedirs(parent_dir, exist_ok=True)

                        # Extract file content safely
                        f = tf.extractfile(member)
                        if f is None:
                            return False

                        # Write to temporary file then rename, or write directly with O_NOFOLLOW
                        # Use os.open with O_WRONLY|O_CREAT|O_EXCL to avoid following symlinks
                        fd = -1
                        try:
                            fd = os.open(normalized_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
                            while True:
                                chunk = f.read(65536)
                                if not chunk:
                                    break
                                os.write(fd, chunk)
                            os.fchmod(fd, member.mode & 0o7777)
                        finally:
                            if fd != -1:
                                os.close(fd)
                            f.close()

                        created_paths.add(normalized_path)
                    except (OSError, IOError, tarfile.TarError):
                        return False

                elif member_obj.issym():
                    try:
                        parent_dir = os.path.dirname(normalized_path)
                        os.makedirs(parent_dir, exist_ok=True)

                        # Remove existing file if any (but not following symlinks)
                        try:
                            os.unlink(normalized_path)
                        except FileNotFoundError:
                            pass
                        except (OSError, IOError):
                            return False

                        os.symlink(symlink_targets[member.name], normalized_path)
                        created_paths.add(normalized_path)
                    except (OSError, IOError):
                        return False

                elif member_obj.islnk():
                    try:
                        parent_dir = os.path.dirname(normalized_path)
                        os.makedirs(parent_dir, exist_ok=True)

                        target_path = hardlink_targets[member.name]

                        # Verify target exists and is a regular file
                        try:
                            st = os.stat(target_path)
                            if not stat.S_ISREG(st.st_mode):
                                return False
                        except (OSError, IOError):
                            return False

                        # Remove existing file if any
                        try:
                            os.unlink(normalized_path)
                        except FileNotFoundError:
                            pass
                        except (OSError, IOError):
                            return False

                        os.link(target_path, normalized_path)
                        created_paths.add(normalized_path)
                    except (OSError, IOError):
                        return False

                else:
                    return False

    except (tarfile.TarError, OSError, IOError):
        return False
    finally:
        try:
            os.close(dest_fd)
        except (OSError, IOError):
            pass

    return True
