import os
import tarfile
import errno
import fcntl

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    # Ensure dest_path exists as a directory and resolve to canonical absolute path
    try:
        os.makedirs(dest_path, exist_ok=True)
        real_dest = os.path.realpath(dest_path)
        if not os.path.isdir(real_dest):
            return False
    except (OSError, ValueError):
        return False

    # Ensure real_dest ends with separator for reliable prefix matching
    dest_prefix = real_dest + os.sep

    # Open and enumerate all members for validation
    try:
        tf = tarfile.open(tar_path, 'r:*')
    except (tarfile.TarError, OSError, IOError):
        return False

    members = tf.getmembers()

    # First pass: validate all members and link targets
    validated_members = []
    validated_symlink_targets = {}  # member -> validated target string
    validated_hardlink_sources = {}  # member -> validated source path

    # Track which archive member names are valid for hard link resolution
    valid_member_names = set()

    for m in members:
        # Reject absolute member names
        if os.path.isabs(m.name):
            tf.close()
            return False

        # Compute normalized absolute extraction path
        member_path = os.path.normpath(os.path.join(real_dest, m.name))
        # Ensure strict prefix match
        if not (member_path + os.sep).startswith(dest_prefix) and member_path != real_dest:
            tf.close()
            return False

        valid_member_names.add(m.name)

    for m in members:
        member_path = os.path.normpath(os.path.join(real_dest, m.name))

        if m.issym() or m.islnk():
            if m.issym():
                # Symbolic link: validate target
                link_target = m.linkname
                if os.path.isabs(link_target):
                    # Absolute target: normalize directly
                    normalized_target = os.path.normpath(link_target)
                else:
                    # Relative target: resolve against parent of member's extraction path
                    parent_dir = os.path.dirname(member_path)
                    normalized_target = os.path.normpath(os.path.join(parent_dir, link_target))

                # Reject if not strictly within dest
                if not (normalized_target + os.sep).startswith(dest_prefix) and normalized_target != real_dest:
                    tf.close()
                    return False

                validated_symlink_targets[m] = link_target  # Use original target string for symlinkat
            else:
                # Hard link: target is another archive member name
                link_source_name = m.linkname
                if os.path.isabs(link_source_name):
                    tf.close()
                    return False

                source_path = os.path.normpath(os.path.join(real_dest, link_source_name))
                if not (source_path + os.sep).startswith(dest_prefix) and source_path != real_dest:
                    tf.close()
                    return False

                # Also reject if source references existing file outside dest_path
                try:
                    if os.path.lexists(source_path):
                        real_source = os.path.realpath(source_path)
                        if not (real_source + os.sep).startswith(dest_prefix) and real_source != real_dest:
                            tf.close()
                            return False
                except (OSError, ValueError):
                    tf.close()
                    return False

                validated_hardlink_sources[m] = source_path
        elif m.isreg() or m.isdir() or m.isfile():
            pass  # Regular file or directory, no additional validation needed
        else:
            # Reject unsupported types: device nodes, FIFOs, etc.
            tf.close()
            return False

        validated_members.append(m)

    # Open directory file descriptor for path-traversal-resistant operations
    try:
        dest_fd = os.open(real_dest, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    except OSError:
        tf.close()
        return False

    try:
        # Helper to get file descriptor for a directory path relative to dest_fd
        def safe_open_dir(path_components):
            """Open a directory relative to dest_fd, following no symlinks."""
            fd = dest_fd
            for comp in path_components:
                if not comp or comp == '.':
                    continue
                try:
                    new_fd = os.open(comp, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=fd)
                except OSError as e:
                    if e.errno == errno.ENOTDIR:
                        return None  # Not a directory
                    raise
                if fd != dest_fd:
                    os.close(fd)
                fd = new_fd
            return fd

        # Helper to create intermediate directories
        def ensure_dir_components(rel_path):
            """Ensure all intermediate directories exist, creating as needed."""
            components = rel_path.split(os.sep)
            # Remove empty components and filename (last component)
            components = [c for c in components if c and c != '.']
            if not components:
                return dest_fd

            # All but last component are directories
            dir_components = components[:-1] if len(components) > 0 else []
            filename = components[-1] if len(components) > 0 else ''

            current_fd = dest_fd
            for i, comp in enumerate(dir_components):
                try:
                    # Try to open as directory
                    new_fd = os.open(comp, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=current_fd)
                except OSError as e:
                    if e.errno == errno.ENOENT:
                        # Need to create directory
                        try:
                            os.mkdir(comp, mode=0o755, dir_fd=current_fd)
                            new_fd = os.open(comp, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=current_fd)
                        except OSError:
                            if current_fd != dest_fd:
                                os.close(current_fd)
                            raise
                    elif e.errno == errno.ENOTDIR:
                        # Component exists but is not a directory
                        if current_fd != dest_fd:
                            os.close(current_fd)
                        return None
                    else:
                        raise
                if current_fd != dest_fd:
                    os.close(current_fd)
                current_fd = new_fd

            return current_fd

        # Second pass: extract members
        for m in validated_members:
            rel_path = m.name
            # Normalize relative path: remove leading ./ and collapse
            rel_path = os.path.normpath(rel_path)
            if rel_path.startswith(os.sep):
                rel_path = rel_path[1:]
            if not rel_path or rel_path == '.':
                continue  # Skip root-level extraction of dest itself

            components = rel_path.split(os.sep)
            components = [c for c in components if c and c != '.']

            if m.isdir():
                # Create directory and all intermediates
                current_fd = dest_fd
                for i, comp in enumerate(components):
                    is_last = (i == len(components) - 1)
                    try:
                        new_fd = os.open(comp, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=current_fd)
                    except OSError as e:
                        if e.errno == errno.ENOENT:
                            try:
                                os.mkdir(comp, mode=m.mode if hasattr(m, 'mode') else 0o755, dir_fd=current_fd)
                                new_fd = os.open(comp, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=current_fd)
                            except OSError:
                                if current_fd != dest_fd:
                                    os.close(current_fd)
                                raise
                        else:
                            raise
                    if current_fd != dest_fd:
                        os.close(current_fd)
                    current_fd = new_fd
                if current_fd != dest_fd:
                    os.close(current_fd)

            elif m.isreg() or m.isfile():
                # Need parent directory fd and filename
                if len(components) == 1:
                    parent_fd = dest_fd
                    filename = components[0]
                else:
                    dir_components = components[:-1]
                    filename = components[-1]
                    parent_fd = safe_open_dir(dir_components)
                    if parent_fd is None:
                        raise OSError(errno.ENOTDIR, "Not a directory")

                try:
                    # Create with O_EXCL to avoid following symlinks or overwriting
                    file_fd = os.open(filename, os.O_CREAT | os.O_WRONLY | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                                      mode=m.mode if hasattr(m, 'mode') else 0o644,
                                      dir_fd=parent_fd)
                except OSError:
                    if parent_fd != dest_fd:
                        os.close(parent_fd)
                    raise

                try:
                    # Extract file contents
                    fobj = tf.extractfile(m)
                    if fobj is not None:
                        try:
                            while True:
                                chunk = fobj.read(65536)
                                if not chunk:
                                    break
                                os.write(file_fd, chunk)
                        finally:
                            fobj.close()
                except OSError:
                    os.close(file_fd)
                    if parent_fd != dest_fd:
                        os.close(parent_fd)
                    raise

                os.close(file_fd)
                if parent_fd != dest_fd:
                    os.close(parent_fd)

            elif m.issym():
                target = validated_symlink_targets[m]
                if len(components) == 1:
                    parent_fd = dest_fd
                    filename = components[0]
                else:
                    dir_components = components[:-1]
                    filename = components[-1]
                    parent_fd = safe_open_dir(dir_components)
                    if parent_fd is None:
                        raise OSError(errno.ENOTDIR, "Not a directory")

                try:
                    os.symlink(target, filename, dir_fd=parent_fd)
                except OSError:
                    if parent_fd != dest_fd:
                        os.close(parent_fd)
                    raise

                if parent_fd != dest_fd:
                    os.close(parent_fd)

            elif m.islnk():
                source_path = validated_hardlink_sources[m]
                if len(components) == 1:
                    dest_link_parent_fd = dest_fd
                    dest_link_name = components[0]
                else:
                    dir_components = components[:-1]
                    dest_link_name = components[-1]
                    dest_link_parent_fd = safe_open_dir(dir_components)
                    if dest_link_parent_fd is None:
                        raise OSError(errno.ENOTDIR, "Not a directory")

                # For linkat, we need source relative to dest_fd or absolute
                # Since source_path is under real_dest, compute relative path
                rel_source = os.path.relpath(source_path, real_dest)
                if rel_source.startswith('..'):
                    # Should not happen due to validation, but be safe
                    if dest_link_parent_fd != dest_fd:
                        os.close(dest_link_parent_fd)
                    raise OSError(errno.EINVAL, "Invalid hard link source")

                source_components = rel_source.split(os.sep)
                source_components = [c for c in source_components if c and c != '.']

                # Open source parent directory
                if len(source_components) == 1:
                    source_parent_fd = dest_fd
                    source_name = source_components[0]
                else:
                    source_dir_components = source_components[:-1]
                    source_name = source_components[-1]
                    source_parent_fd = safe_open_dir(source_dir_components)
                    if source_parent_fd is None:
                        if dest_link_parent_fd != dest_fd:
                            os.close(dest_link_parent_fd)
                        raise OSError(errno.ENOTDIR, "Not a directory")

                try:
                    os.link(source_name, dest_link_name, src_dir_fd=source_parent_fd, dst_dir_fd=dest_link_parent_fd, follow_symlinks=False)
                except OSError:
                    if source_parent_fd != dest_fd:
                        os.close(source_parent_fd)
                    if dest_link_parent_fd != dest_fd:
                        os.close(dest_link_parent_fd)
                    raise

                if source_parent_fd != dest_fd:
                    os.close(source_parent_fd)
                if dest_link_parent_fd != dest_fd:
                    os.close(dest_link_parent_fd)

    except OSError:
        os.close(dest_fd)
        tf.close()
        return False

    os.close(dest_fd)
    tf.close()
    return True
