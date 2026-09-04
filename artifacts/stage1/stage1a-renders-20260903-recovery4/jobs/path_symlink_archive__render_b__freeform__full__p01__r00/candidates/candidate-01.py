import os
import tarfile
import errno
import fcntl

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    # Ensure dest_path exists as a directory and resolve to canonical absolute path
    try:
        os.makedirs(dest_path, exist_ok=True)
        canon_dest = os.path.realpath(os.path.abspath(dest_path))
        if not os.path.isdir(canon_dest):
            return False
    except (OSError, ValueError):
        return False

    # Ensure canon_dest ends with separator for reliable prefix matching
    if not canon_dest.endswith(os.sep):
        canon_dest_prefix = canon_dest + os.sep
    else:
        canon_dest_prefix = canon_dest
        canon_dest = canon_dest.rstrip(os.sep)

    # Open and enumerate all members for validation without extracting
    try:
        tf = tarfile.open(tar_path, 'r:*')
    except (tarfile.TarError, OSError, IOError):
        return False

    members = tf.getmembers()

    # First pass: validate all members and link targets
    validated_members = []
    validated_symlink_targets = {}  # member name -> validated target string
    validated_hardlink_sources = {}  # member name -> validated source path
    regular_file_members = set()  # track regular files for hard link validation

    for member in members:
        # Reject absolute member names
        if os.path.isabs(member.name):
            tf.close()
            return False

        # Compute normalized absolute extraction path
        member_path = os.path.normpath(os.path.join(canon_dest, member.name))

        # Reject if not strictly beneath canon_dest
        if not (member_path + os.sep).startswith(canon_dest_prefix) and member_path != canon_dest:
            tf.close()
            return False

        # Reject unsupported member types
        if member.isdev() or member.isfifo():
            tf.close()
            return False

        if member.issym():
            # Read and validate symlink target
            link_target = member.linkname
            if os.path.isabs(link_target):
                normalized_target = os.path.normpath(link_target)
            else:
                parent_dir = os.path.dirname(member_path)
                normalized_target = os.path.normpath(os.path.join(parent_dir, link_target))

            # Reject if target not strictly within canon_dest
            if not (normalized_target + os.sep).startswith(canon_dest_prefix) and normalized_target != canon_dest:
                tf.close()
                return False

            validated_symlink_targets[member.name] = member.linkname  # use original target string for symlinkat

        elif member.islnk():
            # Hard link: target is another archive member name
            source_name = member.linkname
            if os.path.isabs(source_name):
                tf.close()
                return False

            source_path = os.path.normpath(os.path.join(canon_dest, source_name))

            # Reject if source not strictly beneath canon_dest
            if not (source_path + os.sep).startswith(canon_dest_prefix) and source_path != canon_dest:
                tf.close()
                return False

            # Reject hard links to existing files outside dest_path
            try:
                if os.path.exists(source_path):
                    real_source = os.path.realpath(source_path)
                    if not (real_source + os.sep).startswith(canon_dest_prefix) and real_source != canon_dest:
                        tf.close()
                        return False
            except (OSError, ValueError):
                tf.close()
                return False

            validated_hardlink_sources[member.name] = source_path

        elif member.isfile():
            regular_file_members.add(member.name)

        elif member.isdir():
            pass  # directories are fine
        else:
            # Unknown/unsupported type
            tf.close()
            return False

        validated_members.append(member)

    # Validate hard links point to valid targets (either in archive or existing under dest_path)
    for member in validated_members:
        if member.islnk():
            source_name = member.linkname
            # Check if source is in archive as a regular file
            if source_name not in regular_file_members:
                # Must exist as a real file under dest_path
                source_path = validated_hardlink_sources[member.name]
                try:
                    if not os.path.isfile(source_path):
                        tf.close()
                        return False
                except (OSError, ValueError):
                    tf.close()
                    return False

    # All validation passed, begin extraction
    # Open directory file descriptor for dest_path for path-traversal-resistant operations
    try:
        dest_fd = os.open(canon_dest, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    except OSError:
        tf.close()
        return False

    try:
        for member in validated_members:
            # Split member path into components relative to canon_dest
            rel_path = os.path.relpath(os.path.normpath(os.path.join(canon_dest, member.name)), canon_dest)
            if rel_path == '.':
                continue  # skip if it's dest itself

            components = rel_path.split(os.sep)

            if member.isdir():
                # Create directory with all intermediate components
                current_fd = dest_fd
                try:
                    for i, comp in enumerate(components):
                        if not comp or comp == '.':
                            continue

                        # Try to create directory
                        try:
                            os.mkdir(comp, dir_fd=current_fd)
                        except OSError as e:
                            if e.errno == errno.EEXIST:
                                # Verify it's a real directory, not a symlink
                                try:
                                    stat_info = os.lstat(comp, dir_fd=current_fd)
                                    if not os.path.isdir(stat_info):
                                        return False
                                except OSError:
                                    return False
                            else:
                                return False

                        # Open next level
                        if i < len(components) - 1 or True:  # always need fd for next iteration or final check
                            try:
                                next_fd = os.open(comp, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=current_fd)
                            except OSError:
                                return False

                            if current_fd != dest_fd:
                                os.close(current_fd)
                            current_fd = next_fd

                    if current_fd != dest_fd:
                        os.close(current_fd)

                except Exception:
                    if current_fd != dest_fd:
                        try:
                            os.close(current_fd)
                        except OSError:
                            pass
                    return False

            elif member.isfile():
                # Create intermediate directories
                if len(components) > 1:
                    current_fd = dest_fd
                    try:
                        for comp in components[:-1]:
                            if not comp or comp == '.':
                                continue

                            try:
                                os.mkdir(comp, dir_fd=current_fd)
                            except OSError as e:
                                if e.errno == errno.EEXIST:
                                    try:
                                        stat_info = os.lstat(comp, dir_fd=current_fd)
                                        if not os.path.isdir(stat_info):
                                            return False
                                    except OSError:
                                        return False
                                else:
                                    return False

                            try:
                                next_fd = os.open(comp, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=current_fd)
                            except OSError:
                                return False

                            if current_fd != dest_fd:
                                os.close(current_fd)
                            current_fd = next_fd

                        parent_fd = current_fd
                    except Exception:
                        if current_fd != dest_fd:
                            try:
                                os.close(current_fd)
                            except OSError:
                                pass
                        return False
                else:
                    parent_fd = dest_fd

                # Extract file using O_NOFOLLOW | O_EXCL
                filename = components[-1]
                try:
                    file_fd = os.open(filename, os.O_CREAT | os.O_WRONLY | os.O_NOFOLLOW | os.O_EXCL | os.O_CLOEXEC, member.mode, dir_fd=parent_fd)
                except OSError:
                    if parent_fd != dest_fd:
                        os.close(parent_fd)
                    return False

                try:
                    fobj = tf.extractfile(member)
                    if fobj is None:
                        os.close(file_fd)
                        if parent_fd != dest_fd:
                            os.close(parent_fd)
                        return False

                    while True:
                        chunk = fobj.read(65536)
                        if not chunk:
                            break
                        os.write(file_fd, chunk)

                    fobj.close()
                    os.close(file_fd)

                    # Set permissions
                    try:
                        os.chmod(filename, member.mode, dir_fd=parent_fd)
                    except OSError:
                        pass

                except Exception:
                    try:
                        os.close(file_fd)
                        os.unlink(filename, dir_fd=parent_fd)
                    except OSError:
                        pass
                    if parent_fd != dest_fd:
                        os.close(parent_fd)
                    return False

                if parent_fd != dest_fd:
                    os.close(parent_fd)

            elif member.issym():
                # Create intermediate directories
                if len(components) > 1:
                    current_fd = dest_fd
                    try:
                        for comp in components[:-1]:
                            if not comp or comp == '.':
                                continue

                            try:
                                os.mkdir(comp, dir_fd=current_fd)
                            except OSError as e:
                                if e.errno == errno.EEXIST:
                                    try:
                                        stat_info = os.lstat(comp, dir_fd=current_fd)
                                        if not os.path.isdir(stat_info):
                                            return False
                                    except OSError:
                                        return False
                                else:
                                    return False

                            try:
                                next_fd = os.open(comp, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=current_fd)
                            except OSError:
                                return False

                            if current_fd != dest_fd:
                                os.close(current_fd)
                            current_fd = next_fd

                        parent_fd = current_fd
                    except Exception:
                        if current_fd != dest_fd:
                            try:
                                os.close(current_fd)
                            except OSError:
                                pass
                        return False
                else:
                    parent_fd = dest_fd

                filename = components[-1]
                target = validated_symlink_targets[member.name]

                try:
                    os.symlink(target, filename, dir_fd=parent_fd)
                except OSError:
                    if parent_fd != dest_fd:
                        os.close(parent_fd)
                    return False

                if parent_fd != dest_fd:
                    os.close(parent_fd)

            elif member.islnk():
                # Hard link extraction
                source_path = validated_hardlink_sources[member.name]
                source_rel = os.path.relpath(source_path, canon_dest)
                source_components = source_rel.split(os.sep)

                if len(components) > 1:
                    current_fd = dest_fd
                    try:
                        for comp in components[:-1]:
                            if not comp or comp == '.':
                                continue

                            try:
                                os.mkdir(comp, dir_fd=current_fd)
                            except OSError as e:
                                if e.errno == errno.EEXIST:
                                    try:
                                        stat_info = os.lstat(comp, dir_fd=current_fd)
                                        if not os.path.isdir(stat_info):
                                            return False
                                    except OSError:
                                        return False
                                else:
                                    return False

                            try:
                                next_fd = os.open(comp, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=current_fd)
                            except OSError:
                                return False

                            if current_fd != dest_fd:
                                os.close(current_fd)
                            current_fd = next_fd

                        parent_fd = current_fd
                    except Exception:
                        if current_fd != dest_fd:
                            try:
                                os.close(current_fd)
                            except OSError:
                                pass
                        return False
                else:
                    parent_fd = dest_fd

                dest_filename = components[-1]

                # Need source file descriptor for linkat
                if len(source_components) > 1:
                    current_fd = dest_fd
                    try:
                        for comp in source_components[:-1]:
                            if not comp or comp == '.':
                                continue
                            next_fd = os.open(comp, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=current_fd)
                            if current_fd != dest_fd:
                                os.close(current_fd)
                            current_fd = next_fd
                        source_parent_fd = current_fd
                    except OSError:
                        if current_fd != dest_fd:
                            try:
                                os.close(current_fd)
                            except OSError:
                                pass
                        if parent_fd != dest_fd:
                            os.close(parent_fd)
                        return False
                else:
                    source_parent_fd = dest_fd

                source_filename = source_components[-1]

                try:
                    os.link(source_filename, dest_filename, src_dir_fd=source_parent_fd, dst_dir_fd=parent_fd, follow_symlinks=False)
                except OSError:
                    if source_parent_fd != dest_fd:
                        os.close(source_parent_fd)
                    if parent_fd != dest_fd:
                        os.close(parent_fd)
                    return False

                if source_parent_fd != dest_fd:
                    os.close(source_parent_fd)
                if parent_fd != dest_fd:
                    os.close(parent_fd)

    finally:
        try:
            os.close(dest_fd)
        except OSError:
            pass

    tf.close()
    return True
