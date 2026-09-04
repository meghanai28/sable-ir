import os
import tarfile
from os.path import normpath, join, dirname, isabs, sep


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    # Step 1: Resolve safe_dest
    safe_dest = normpath(os.path.abspath(dest_path))
    if not safe_dest.endswith(sep):
        safe_dest_prefix = safe_dest + sep
    else:
        safe_dest_prefix = safe_dest
        safe_dest = safe_dest.rstrip(sep)
        if safe_dest == '':
            safe_dest = sep

    def is_inside_safe(path: str) -> bool:
        """Check if path is safe_dest or properly nested within it."""
        if path == safe_dest:
            return True
        if path.startswith(safe_dest_prefix):
            # Ensure true boundary: character after prefix must be sep or we are at exact match
            next_char_idx = len(safe_dest_prefix)
            if next_char_idx < len(path) and path[next_char_idx] == sep:
                return True
            # Handle case where safe_dest already ends with sep
            if safe_dest.endswith(sep) and path.startswith(safe_dest):
                remainder = path[len(safe_dest):]
                if remainder.startswith(sep) or remainder == '':
                    return True
        return False

    def sanitize_member_name(name: str) -> str:
        """Strip leading path separators and, on Windows, any drive letter."""
        # Strip leading separators
        while name.startswith('/') or name.startswith('\\'):
            name = name[1:]
        # On Windows, strip drive letter
        if os.name == 'nt' or (hasattr(os, 'name') and os.name == 'nt'):
            if len(name) >= 2 and name[1] == ':':
                name = name[2:]
                while name.startswith('/') or name.startswith('\\'):
                    name = name[1:]
        return name

    def resolve_symlink_target(link_target: str, extract_path: str) -> str:
        """Resolve symlink target relative to parent of extract_path, return absolute normalized path."""
        parent = dirname(extract_path)
        if isabs(link_target):
            # Absolute link target: sanitize and check
            sanitized = sanitize_member_name(link_target)
            resolved = normpath(join(safe_dest, sanitized))
        else:
            resolved = normpath(join(parent, link_target))
        return resolved

    # Steps 2-3: Open archive and validate all members
    try:
        tf = tarfile.open(tar_path, mode='r:*')
    except (tarfile.TarError, OSError, IOError):
        return False

    try:
        members = tf.getmembers()
    except (tarfile.TarError, OSError, IOError):
        tf.close()
        return False

    # Validation pass
    manifest = {}  # Maps member to (extract_path, link_target_or_none, hardlink_target_or_none)
    path_to_member = {}  # Maps extract_path to member info for hardlink resolution
    dirs_to_create = set()
    regular_files = []
    symlinks = []
    hardlinks = []

    for member in members:
        # Sanitize member name
        sanitized_name = sanitize_member_name(member.name)
        if sanitized_name == '':
            # Empty name after sanitization - reject
            tf.close()
            return False

        extract_path = normpath(join(safe_dest, sanitized_name))

        # Validate extract_path is inside safe_dest
        if not is_inside_safe(extract_path):
            tf.close()
            return False

        # Determine member type
        if member.issym() or member.islnk():
            # Symbolic link or hard link
            if member.issym():
                # Symbolic link
                link_target = member.linkname
                resolved_target = resolve_symlink_target(link_target, extract_path)
                if not is_inside_safe(resolved_target):
                    tf.close()
                    return False
                # Also validate that the link target path doesn't escape through normalization tricks
                # Re-check with strict prefix match
                if resolved_target != safe_dest and not resolved_target.startswith(safe_dest_prefix):
                    tf.close()
                    return False
                manifest[member] = (extract_path, resolved_target, None)
                symlinks.append(member)
                # Need parent directory
                parent = dirname(extract_path)
                if parent != safe_dest and is_inside_safe(parent):
                    dirs_to_create.add(parent)
            else:
                # Hard link
                sanitized_link_name = sanitize_member_name(member.linkname)
                if sanitized_link_name == '':
                    tf.close()
                    return False
                target_path = normpath(join(safe_dest, sanitized_link_name))
                if not is_inside_safe(target_path):
                    tf.close()
                    return False
                # Hard link target must not be a symbolic link in the archive
                # We need to check if target_path corresponds to a symlink member
                manifest[member] = (extract_path, None, target_path)
                hardlinks.append(member)
                # Need parent directory
                parent = dirname(extract_path)
                if parent != safe_dest and is_inside_safe(parent):
                    dirs_to_create.add(parent)
        elif member.isdir():
            # Directory
            manifest[member] = (extract_path, None, None)
            dirs_to_create.add(extract_path)
            # Also ensure parent exists
            parent = dirname(extract_path)
            if parent != safe_dest and is_inside_safe(parent):
                dirs_to_create.add(parent)
        elif member.isfile() or member.isreg():
            # Regular file
            manifest[member] = (extract_path, None, None)
            regular_files.append(member)
            # Need parent directory
            parent = dirname(extract_path)
            if parent != safe_dest and is_inside_safe(parent):
                dirs_to_create.add(parent)
        else:
            # Reject device nodes, FIFOs, and other non-standard types
            tf.close()
            return False

    # Build path_to_member for hardlink validation
    for member, (extract_path, _, _) in manifest.items():
        path_to_member[extract_path] = member

    # Validate hard links: target must exist in archive and not be a symlink
    for member in hardlinks:
        _, _, target_path = manifest[member]
        if target_path not in path_to_member:
            tf.close()
            return False
        target_member = path_to_member[target_path]
        if target_member.issym():
            tf.close()
            return False

    # Step 4: Extraction pass in dependency order
    # First: directories and parent directories
    # Sort to create parents before children
    sorted_dirs = sorted(dirs_to_create, key=lambda x: len(x.split(sep)))
    for dir_path in sorted_dirs:
        try:
            # Use os.makedirs with exist_ok, but we need to be careful about symlinks
            # Check if something exists at dir_path
            if os.path.islink(dir_path):
                # A symlink exists where we want a directory - this is a potential attack
                # Check if it points inside safe_dest
                link_dest = os.readlink(dir_path)
                resolved_link = normpath(join(dirname(dir_path), link_dest))
                if not is_inside_safe(resolved_link):
                    tf.close()
                    return False
                # Even if inside, we shouldn't follow it for directory creation
                # Remove the symlink and create directory
                os.unlink(dir_path)
            # Create directory with proper permissions, don't follow symlinks
            os.makedirs(dir_path, exist_ok=True)
            # Verify it's actually a directory now
            if not os.path.isdir(dir_path):
                tf.close()
                return False
        except (OSError, IOError):
            tf.close()
            return False

    # Second: regular files
    for member in regular_files:
        extract_path, _, _ = manifest[member]
        try:
            # Ensure parent directory exists
            parent = dirname(extract_path)
            if parent != safe_dest and not os.path.isdir(parent):
                # Try to create parent
                try:
                    os.makedirs(parent, exist_ok=True)
                except (OSError, IOError):
                    tf.close()
                    return False

            # Open file with O_NOFOLLOW to avoid following symlinks
            # Use os.open with O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW if available
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            if hasattr(os, 'O_NOFOLLOW'):
                flags |= os.O_NOFOLLOW

            try:
                fd = os.open(extract_path, flags, 0o666)
            except (OSError, IOError) as e:
                # If file exists, we might need to handle it
                # For security, don't overwrite existing files that might be symlinks
                if os.path.exists(extract_path):
                    if os.path.islink(extract_path):
                        # Remove symlink and retry
                        os.unlink(extract_path)
                        fd = os.open(extract_path, flags, 0o666)
                    elif os.path.isfile(extract_path):
                        # Overwrite regular file
                        fd = os.open(extract_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, 'O_NOFOLLOW', 0), 0o666)
                    else:
                        tf.close()
                        return False
                else:
                    tf.close()
                    return False

            try:
                with os.fdopen(fd, 'wb') as f:
                    # Extract file content
                    fileobj = tf.extractfile(member)
                    if fileobj is None:
                        os.close(fd)
                        tf.close()
                        return False
                    try:
                        while True:
                            chunk = fileobj.read(65536)
                            if not chunk:
                                break
                            f.write(chunk)
                    finally:
                        fileobj.close()
            except:
                try:
                    os.close(fd)
                except:
                    pass
                raise

            # Set permissions if available
            try:
                if member.mode:
                    os.chmod(extract_path, member.mode)
            except (OSError, IOError):
                pass

        except (OSError, IOError, tarfile.TarError):
            tf.close()
            return False

    # Third: symbolic links
    for member in symlinks:
        extract_path, resolved_target, _ = manifest[member]
        try:
            # Ensure parent directory exists
            parent = dirname(extract_path)
            if parent != safe_dest and not os.path.isdir(parent):
                try:
                    os.makedirs(parent, exist_ok=True)
                except (OSError, IOError):
                    tf.close()
                    return False

            # Remove existing file/symlink if present
            try:
                if os.path.lexists(extract_path):
                    if os.path.islink(extract_path) or os.path.isfile(extract_path) or os.path.isdir(extract_path):
                        # On Unix, use os.unlink; on Windows, may need different handling
                        if os.path.isdir(extract_path) and not os.path.islink(extract_path):
                            os.rmdir(extract_path)
                        else:
                            os.unlink(extract_path)
            except (OSError, IOError):
                pass

            # Create symbolic link with original link target string (not resolved)
            # The pre-validation ensures the resolved path is safe
            os.symlink(member.linkname, extract_path)
        except (OSError, IOError, NotImplementedError):
            tf.close()
            return False

    # Fourth: hard links
    for member in hardlinks:
        extract_path, _, target_path = manifest[member]
        try:
            # Ensure parent directory exists
            parent = dirname(extract_path)
            if parent != safe_dest and not os.path.isdir(parent):
                try:
                    os.makedirs(parent, exist_ok=True)
                except (OSError, IOError):
                    tf.close()
                    return False

            # Remove existing file if present
            try:
                if os.path.lexists(extract_path):
                    if os.path.isdir(extract_path) and not os.path.islink(extract_path):
                        os.rmdir(extract_path)
                    else:
                        os.unlink(extract_path)
            except (OSError, IOError):
                pass

            # Verify target exists and is a regular file (not symlink)
            if not os.path.exists(target_path) or os.path.islink(target_path):
                tf.close()
                return False

            # Create hard link
            os.link(target_path, extract_path)
        except (OSError, IOError):
            tf.close()
            return False

    tf.close()
    return True
