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

    if not os.path.isdir(base):
        return False

    base_prefix = base + path_separator

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

    # Build manifest with computed paths and validation data
    manifest = []
    regular_file_members = set()  # Set of validated member_path strings for regular files

    # First pass: validation
    for m in members:
        # Skip empty members and dot-only names early
        if not m.name or m.name == '.' or m.name == './':
            tf.close()
            return False

        # Member path validation
        try:
            member_path = os.path.normpath(os.path.join(base, m.name))
        except (OSError, ValueError):
            tf.close()
            return False

        if not member_path.startswith(base_prefix):
            tf.close()
            return False

        # Type filtering
        if m.isreg():
            member_type = 'reg'
            regular_file_members.add(member_path)
        elif m.isdir():
            member_type = 'dir'
        elif m.issym():
            member_type = 'sym'
        elif m.islnk():
            member_type = 'lnk'
        else:
            # Reject block devices, character devices, FIFOs, unknown types
            tf.close()
            return False

        # Symbolic-link target validation
        if member_type == 'sym':
            raw_target = m.linkname
            try:
                if os.path.isabs(raw_target):
                    link_target = os.path.normpath(raw_target)
                else:
                    link_target = os.path.normpath(os.path.join(os.path.dirname(member_path), raw_target))
            except (OSError, ValueError):
                tf.close()
                return False

            if not link_target.startswith(base_prefix):
                tf.close()
                return False

            manifest.append({
                'member': m,
                'member_path': member_path,
                'type': member_type,
                'link_target': raw_target,  # Store raw target for creation
            })
            continue

        # Hard-link target validation
        if member_type == 'lnk':
            try:
                link_target = os.path.normpath(os.path.join(base, m.linkname))
            except (OSError, ValueError):
                tf.close()
                return False

            if not link_target.startswith(base_prefix):
                tf.close()
                return False

            if link_target not in regular_file_members:
                tf.close()
                return False

            manifest.append({
                'member': m,
                'member_path': member_path,
                'type': member_type,
                'link_target': link_target,
            })
            continue

        # Regular file or directory
        manifest.append({
            'member': m,
            'member_path': member_path,
            'type': member_type,
        })

    # Step 4: Second pass - extraction
    for entry in manifest:
        m = entry['member']
        member_path = entry['member_path']
        member_type = entry['type']

        # Determine parent directory path
        parent_dir = os.path.dirname(member_path)

        # Verify/create parent directory path components starting from base
        if parent_dir != base:
            rel_path = os.path.relpath(parent_dir, base)
            components = rel_path.split(path_separator)
        else:
            components = []

        current_dir_fd = None
        try:
            # Open base directory
            current_dir_fd = os.open(base, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        except OSError:
            tf.close()
            return False

        # Walk/create components
        for component in components:
            if not component or component == '.':
                os.close(current_dir_fd)
                tf.close()
                return False

            try:
                # Try to open existing directory component without following symlinks
                next_dir_fd = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current_dir_fd)
                os.close(current_dir_fd)
                current_dir_fd = next_dir_fd
            except OSError as e:
                if e.errno == errno.ENOTDIR or e.errno == errno.ELOOP:
                    # Not a directory or is a symlink
                    os.close(current_dir_fd)
                    tf.close()
                    return False
                elif e.errno == errno.ENOENT:
                    # Need to create directory
                    try:
                        os.mkdir(component, dir_fd=current_dir_fd)
                    except OSError:
                        os.close(current_dir_fd)
                        tf.close()
                        return False
                    try:
                        next_dir_fd = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current_dir_fd)
                        os.close(current_dir_fd)
                        current_dir_fd = next_dir_fd
                    except OSError:
                        os.close(current_dir_fd)
                        tf.close()
                        return False
                else:
                    os.close(current_dir_fd)
                    tf.close()
                    return False

        # Now current_dir_fd is the verified parent directory
        final_name = os.path.basename(member_path)

        try:
            if member_type == 'dir':
                try:
                    os.mkdir(final_name, dir_fd=current_dir_fd)
                except OSError as e:
                    if e.errno == errno.EEXIST:
                        # Verify existing is a real directory
                        try:
                            fd = os.open(final_name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current_dir_fd)
                            os.close(fd)
                        except OSError:
                            os.close(current_dir_fd)
                            tf.close()
                            return False
                    else:
                        os.close(current_dir_fd)
                        tf.close()
                        return False

            elif member_type == 'reg':
                # Open with O_NOFOLLOW|O_CREAT|O_WRONLY, mode from tarinfo
                mode = (m.mode & 0o777) if m.mode else 0o644
                try:
                    fd = os.open(final_name, os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | os.O_EXCL, mode, dir_fd=current_dir_fd)
                except OSError as e:
                    os.close(current_dir_fd)
                    tf.close()
                    return False

                try:
                    f = os.fdopen(fd, 'wb')
                except OSError:
                    os.close(fd)
                    os.close(current_dir_fd)
                    tf.close()
                    return False

                try:
                    fobj = tf.extractfile(m)
                    if fobj is None:
                        f.close()
                        os.close(current_dir_fd)
                        tf.close()
                        return False

                    while True:
                        chunk = fobj.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                except (OSError, IOError):
                    f.close()
                    os.close(current_dir_fd)
                    tf.close()
                    return False
                finally:
                    f.close()

            elif member_type == 'sym':
                raw_target = entry['link_target']
                try:
                    os.symlink(raw_target, final_name, dir_fd=current_dir_fd)
                except OSError:
                    os.close(current_dir_fd)
                    tf.close()
                    return False

            elif member_type == 'lnk':
                link_target = entry['link_target']
                # Verify target exists and is a regular file (not symlink) using lstat equivalent
                try:
                    target_fd = os.open(link_target, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
                    try:
                        stat_info = os.fstat(target_fd)
                        if not os.path.isfile(link_target):
                            # Use fstat to check if regular file
                            import stat
                            if not stat.S_ISREG(stat_info.st_mode):
                                os.close(target_fd)
                                os.close(current_dir_fd)
                                tf.close()
                                return False
                    finally:
                        os.close(target_fd)
                except OSError:
                    os.close(current_dir_fd)
                    tf.close()
                    return False

                # Create hard link
                try:
                    os.link(link_target, member_path, follow_symlinks=False)
                except (OSError, TypeError):
                    # Fallback for older Python without follow_symlinks
                    try:
                        os.link(link_target, member_path)
                    except OSError:
                        os.close(current_dir_fd)
                        tf.close()
                        return False

            os.close(current_dir_fd)

        except Exception:
            try:
                os.close(current_dir_fd)
            except:
                pass
            tf.close()
            return False

    tf.close()
    return True
