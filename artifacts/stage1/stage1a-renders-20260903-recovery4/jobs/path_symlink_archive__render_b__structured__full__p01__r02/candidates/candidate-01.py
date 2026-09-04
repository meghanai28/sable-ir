import os
import tarfile
import errno
import fcntl


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    path_separator = os.sep

    # Step 1: Resolve dest_path to canonical absolute path base
    try:
        real_dest = os.path.realpath(dest_path)
        base = os.path.normpath(real_dest)
    except (OSError, ValueError):
        return False

    # Verify base is a directory
    try:
        if not os.path.isdir(base):
            return False
    except OSError:
        return False

    base_with_sep = base + path_separator

    # Helper to check if path is strictly inside base
    def is_inside(path: str) -> bool:
        return path.startswith(base_with_sep)

    # Step 2: Open tar archive and read manifest
    try:
        tf = tarfile.open(tar_path, 'r:*')
    except (tarfile.TarError, OSError, IOError):
        return False

    try:
        members = tf.getmembers()
    except (tarfile.TarError, OSError, IOError):
        tf.close()
        return False

    # Build manifest with computed paths and validate structure
    manifest = []
    hard_link_targets = set()  # Set of validated hard link target paths
    regular_file_paths = set()  # Set of member paths that are regular files

    # First pass: validation
    for m in members:
        # Skip empty names and dot-only names early
        if not m.name or m.name == '.' or m.name == './':
            tf.close()
            return False

        # Compute member path
        try:
            member_path = os.path.normpath(os.path.join(base, m.name))
        except (ValueError, OSError):
            tf.close()
            return False

        # Validate member path is inside base
        if not is_inside(member_path):
            tf.close()
            return False

        # Type filtering
        if m.issym() or m.islnk():
            pass  # Allowed
        elif m.isdir():
            pass  # Allowed
        elif m.isfile():
            pass  # Allowed
        else:
            # Reject block devices, char devices, FIFOs, unknown types
            tf.close()
            return False

        # Collect regular file paths for hard link validation
        if m.isfile():
            regular_file_paths.add(member_path)

        manifest.append((m, member_path))

    # Validate symbolic links and hard links
    for m, member_path in manifest:
        if m.issym():
            raw_target = m.linkname
            if raw_target is None:
                tf.close()
                return False

            if os.path.isabs(raw_target):
                try:
                    link_target = os.path.normpath(raw_target)
                except (ValueError, OSError):
                    tf.close()
                    return False
            else:
                try:
                    link_target = os.path.normpath(os.path.join(os.path.dirname(member_path), raw_target))
                except (ValueError, OSError):
                    tf.close()
                    return False

            if not is_inside(link_target):
                tf.close()
                return False

        elif m.islnk():
            if m.linkname is None:
                tf.close()
                return False

            try:
                link_target = os.path.normpath(os.path.join(base, m.linkname))
            except (ValueError, OSError):
                tf.close()
                return False

            if not is_inside(link_target):
                tf.close()
                return False

            # Hard link target must correspond to a regular-file member in the same archive
            if link_target not in regular_file_paths:
                tf.close()
                return False

            hard_link_targets.add(link_target)

    # Step 4: Second pass - extraction
    # Helper functions for safe directory operations

    def safe_mkdir_at(dirfd, name, mode=0o777):
        """Create directory relative to dirfd without following symlinks."""
        try:
            os.mkdir(name, mode, dir_fd=dirfd)
            return True
        except OSError as e:
            if e.errno == errno.EEXIST:
                return True
            return False

    def open_dir_fd(path):
        """Open a directory and return its file descriptor."""
        try:
            return os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        except OSError:
            return None

    def is_real_dir(path, dirfd=None):
        """Check if path relative to dirfd is a real directory (not symlink)."""
        try:
            if dirfd is not None:
                st = os.lstat(path, dir_fd=dirfd)
            else:
                st = os.lstat(path)
            return stat.S_ISDIR(st.st_mode)
        except OSError:
            return False

    def safe_openat(dirfd, name, flags, mode=0o666):
        """Open file relative to dirfd without following terminal symlink."""
        try:
            return os.open(name, flags | os.O_NOFOLLOW, mode, dir_fd=dirfd)
        except OSError:
            return -1

    import stat

    # Track created directories to avoid redundant checks
    verified_dirs = {base}

    for m, member_path in manifest:
        # Compute parent directory path
        parent_dir = os.path.dirname(member_path)
        member_name = os.path.basename(member_path)

        # Walk from base to parent_dir, verifying/creating each component
        rel_parts = []
        current = parent_dir
        while current != base:
            if not is_inside(current):
                tf.close()
                return False
            if current == base_with_sep or current == base:
                break
            head, tail = os.path.split(current)
            if not tail:
                break
            rel_parts.append(tail)
            current = head

        rel_parts.reverse()

        # Open base directory
        try:
            base_fd = os.open(base, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        except OSError:
            tf.close()
            return False

        current_fd = base_fd
        current_path = base

        try:
            for part in rel_parts:
                # Verify current_fd is still a real directory
                try:
                    st = os.fstat(current_fd)
                    if not stat.S_ISDIR(st.st_mode):
                        os.close(current_fd)
                        tf.close()
                        return False
                except OSError:
                    os.close(current_fd)
                    tf.close()
                    return False

                # Check if part exists and is a real directory
                try:
                    st = os.lstat(part, dir_fd=current_fd)
                    if not stat.S_ISDIR(st.st_mode):
                        os.close(current_fd)
                        tf.close()
                        return False
                except OSError as e:
                    if e.errno == errno.ENOENT:
                        # Create directory
                        try:
                            os.mkdir(part, 0o777, dir_fd=current_fd)
                        except OSError:
                            os.close(current_fd)
                            tf.close()
                            return False
                    else:
                        os.close(current_fd)
                        tf.close()
                        return False

                # Open next directory
                try:
                    next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=current_fd)
                except OSError:
                    os.close(current_fd)
                    tf.close()
                    return False

                os.close(current_fd)
                current_fd = next_fd
                current_path = os.path.join(current_path, part)
                verified_dirs.add(current_path)

            # Verify final parent is a real directory
            try:
                st = os.fstat(current_fd)
                if not stat.S_ISDIR(st.st_mode):
                    os.close(current_fd)
                    tf.close()
                    return False
            except OSError:
                os.close(current_fd)
                tf.close()
                return False

            # Now create the member
            if m.isdir():
                # Create directory if it doesn't exist
                try:
                    os.mkdir(member_name, 0o777, dir_fd=current_fd)
                except OSError as e:
                    if e.errno != errno.EEXIST:
                        os.close(current_fd)
                        tf.close()
                        return False
                    # If exists, verify it's a real directory
                    try:
                        st = os.lstat(member_name, dir_fd=current_fd)
                        if not stat.S_ISDIR(st.st_mode):
                            os.close(current_fd)
                            tf.close()
                            return False
                    except OSError:
                        os.close(current_fd)
                        tf.close()
                        return False

            elif m.isfile():
                # Open file with O_NOFOLLOW | O_CREAT | O_WRONLY | O_TRUNC
                try:
                    file_fd = os.open(member_name, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW | os.O_CLOEXEC, 0o666, dir_fd=current_fd)
                except OSError:
                    os.close(current_fd)
                    tf.close()
                    return False

                # Extract file content
                try:
                    fobj = tf.extractfile(m)
                    if fobj is None:
                        os.close(file_fd)
                        os.close(current_fd)
                        tf.close()
                        return False

                    while True:
                        chunk = fobj.read(65536)
                        if not chunk:
                            break
                        try:
                            os.write(file_fd, chunk)
                        except OSError:
                            fobj.close()
                            os.close(file_fd)
                            os.close(current_fd)
                            tf.close()
                            return False
                    fobj.close()
                except (OSError, IOError):
                    os.close(file_fd)
                    os.close(current_fd)
                    tf.close()
                    return False

                try:
                    os.close(file_fd)
                except OSError:
                    os.close(current_fd)
                    tf.close()
                    return False

            elif m.issym():
                # Create symbolic link
                raw_target = m.linkname
                try:
                    os.symlink(raw_target, member_name, dir_fd=current_fd)
                except OSError as e:
                    if e.errno == errno.EEXIST:
                        # Remove existing and recreate
                        try:
                            os.unlink(member_name, dir_fd=current_fd)
                            os.symlink(raw_target, member_name, dir_fd=current_fd)
                        except OSError:
                            os.close(current_fd)
                            tf.close()
                            return False
                    else:
                        os.close(current_fd)
                        tf.close()
                        return False

            elif m.islnk():
                # Hard link: validate target exists and is regular file
                link_target = os.path.normpath(os.path.join(base, m.linkname))
                if not is_inside(link_target):
                    os.close(current_fd)
                    tf.close()
                    return False

                # Verify target is not a symlink and is a regular file
                try:
                    target_st = os.lstat(link_target)
                    if not stat.S_ISREG(target_st.st_mode):
                        os.close(current_fd)
                        tf.close()
                        return False
                except OSError:
                    os.close(current_fd)
                    tf.close()
                    return False

                # Create hard link
                try:
                    os.link(link_target, os.path.join(current_path, member_name))
                except OSError as e:
                    if e.errno == errno.EEXIST:
                        try:
                            os.unlink(member_name, dir_fd=current_fd)
                            os.link(link_target, os.path.join(current_path, member_name))
                        except OSError:
                            os.close(current_fd)
                            tf.close()
                            return False
                    else:
                        os.close(current_fd)
                        tf.close()
                        return False

            os.close(current_fd)

        except Exception:
            try:
                os.close(current_fd)
            except:
                pass
            tf.close()
            return False

    tf.close()
    return True
