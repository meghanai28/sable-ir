import os
import tarfile
import errno
import fcntl


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    # Step 1: Resolve dest_path to canonical absolute path base
    try:
        base = os.path.realpath(os.path.abspath(dest_path))
    except (OSError, ValueError):
        return False
    
    if not os.path.isdir(base):
        return False
    
    path_sep = os.sep
    base_prefix = base + path_sep
    
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
    
    # Prepare manifest data structures
    manifest = []  # list of (member, member_path, member_type_info)
    regular_file_members = set()  # set of normalized paths for regular files in archive
    
    # First, collect regular file paths for hard-link validation
    for m in members:
        try:
            member_path = os.path.normpath(os.path.join(base, m.name))
        except (ValueError, OSError):
            tf.close()
            return False
        
        # Check for valid member path
        if not member_path.startswith(base_prefix):
            tf.close()
            return False
        
        # Determine type
        if m.isfile():
            regular_file_members.add(member_path)
        elif m.isdir():
            pass
        elif m.issym():
            pass
        elif m.islnk():
            pass
        elif m.isdev() or m.isfifo() or m.ischr() or m.isblk():
            # Unsupported type - will be rejected in validation
            pass
        else:
            # Unknown type
            pass
    
    # Step 3: First pass - pre-extraction validation
    validated_manifest = []
    
    for m in members:
        # Member path validation
        try:
            member_path = os.path.normpath(os.path.join(base, m.name))
        except (ValueError, OSError):
            tf.close()
            return False
        
        # Reject absolute member names, empty names, dot-only names, traversal escapes
        if not member_path.startswith(base_prefix):
            tf.close()
            return False
        
        # Type filtering
        if m.isfile():
            member_type = 'file'
        elif m.isdir():
            member_type = 'dir'
        elif m.issym():
            member_type = 'symlink'
        elif m.islnk():
            member_type = 'hardlink'
        else:
            # Reject block devices, character devices, FIFOs, unknown types
            tf.close()
            return False
        
        # Symbolic-link target validation
        if member_type == 'symlink':
            raw_target = m.linkname
            try:
                if os.path.isabs(raw_target):
                    link_target = os.path.normpath(raw_target)
                else:
                    link_target = os.path.normpath(os.path.join(os.path.dirname(member_path), raw_target))
            except (ValueError, OSError):
                tf.close()
                return False
            
            if not link_target.startswith(base_prefix):
                tf.close()
                return False
        
        # Hard-link target validation
        if member_type == 'hardlink':
            try:
                link_target = os.path.normpath(os.path.join(base, m.linkname))
            except (ValueError, OSError):
                tf.close()
                return False
            
            if not link_target.startswith(base_prefix):
                tf.close()
                return False
            
            if link_target not in regular_file_members:
                tf.close()
                return False
        
        validated_manifest.append((m, member_path, member_type))
    
    # Step 4: Second pass - extraction with guards
    # We need to track created directories and handle extraction
    # Use directory file descriptors for safe operations
    
    def get_dir_fd_at_path(path):
        """Open a directory and return its fd, or -1 on failure."""
        try:
            return os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        except OSError:
            return -1
    
    def verify_and_ensure_parent_dir(member_path):
        """Verify/create parent directories, return (parent_fd, final_name) or (None, None) on failure."""
        # Get relative path from base
        rel_path = member_path[len(base_prefix):]
        components = rel_path.split(path_sep)
        final_name = components[-1]
        parent_components = components[:-1]
        
        # Start from base
        current_path = base
        current_fd = get_dir_fd_at_path(current_path)
        if current_fd < 0:
            return (None, None)
        
        try:
            for comp in parent_components:
                if not comp:
                    continue
                
                # Try to open existing subdirectory
                try:
                    next_fd = os.open(comp, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current_fd)
                except OSError as e:
                    if e.errno == errno.ENOENT:
                        # Need to create directory
                        try:
                            os.mkdir(comp, 0o755, dir_fd=current_fd)
                        except OSError:
                            os.close(current_fd)
                            return (None, None)
                        
                        try:
                            next_fd = os.open(comp, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current_fd)
                        except OSError:
                            os.close(current_fd)
                            return (None, None)
                    else:
                        os.close(current_fd)
                        return (None, None)
                
                # Verify it's a real directory (not symlink) - O_NOFOLLOW ensures this
                # But double-check with fstat
                try:
                    st = os.fstat(next_fd)
                    if not os.path.isdir(st.st_mode):
                        os.close(next_fd)
                        os.close(current_fd)
                        return (None, None)
                except OSError:
                    os.close(next_fd)
                    os.close(current_fd)
                    return (None, None)
                
                os.close(current_fd)
                current_fd = next_fd
                current_path = os.path.join(current_path, comp)
            
            return (current_fd, final_name)
        except Exception:
            if current_fd >= 0:
                os.close(current_fd)
            return (None, None)
    
    # Track hard link targets that exist on disk (created during extraction or pre-existing)
    # For validation at hard-link creation time
    
    for m, member_path, member_type in validated_manifest:
        parent_fd, final_name = verify_and_ensure_parent_dir(member_path)
        if parent_fd is None:
            tf.close()
            return False
        
        try:
            if member_type == 'dir':
                # Check if directory already exists
                try:
                    existing_fd = os.open(final_name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
                    # Verify it's a directory
                    try:
                        st = os.fstat(existing_fd)
                        if not os.path.isdir(st.st_mode):
                            os.close(existing_fd)
                            os.close(parent_fd)
                            tf.close()
                            return False
                    except OSError:
                        os.close(existing_fd)
                        os.close(parent_fd)
                        tf.close()
                        return False
                    os.close(existing_fd)
                except OSError as e:
                    if e.errno == errno.ENOENT:
                        # Create directory
                        try:
                            os.mkdir(final_name, m.mode if hasattr(m, 'mode') else 0o755, dir_fd=parent_fd)
                        except OSError:
                            os.close(parent_fd)
                            tf.close()
                            return False
                    else:
                        os.close(parent_fd)
                        tf.close()
                        return False
            
            elif member_type == 'file':
                # Open with O_NOFOLLOW | O_CREAT | O_WRONLY, fail if exists
                # Use O_EXCL to prevent following symlinks
                try:
                    file_fd = os.open(final_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 
                                     m.mode if hasattr(m, 'mode') else 0o644, dir_fd=parent_fd)
                except OSError:
                    os.close(parent_fd)
                    tf.close()
                    return False
                
                try:
                    # Stream content from tar
                    fobj = tf.extractfile(m)
                    if fobj is None:
                        os.close(file_fd)
                        os.close(parent_fd)
                        tf.close()
                        return False
                    
                    try:
                        while True:
                            chunk = fobj.read(65536)
                            if not chunk:
                                break
                            os.write(file_fd, chunk)
                    finally:
                        fobj.close()
                except (OSError, IOError):
                    os.close(file_fd)
                    os.close(parent_fd)
                    tf.close()
                    return False
                
                os.close(file_fd)
            
            elif member_type == 'symlink':
                # Create symlink with raw validated target
                raw_target = m.linkname
                try:
                    os.symlink(raw_target, final_name, dir_fd=parent_fd)
                except OSError:
                    # If it already exists, check if it's the same symlink
                    try:
                        existing_target = os.readlink(final_name, dir_fd=parent_fd)
                        if existing_target != raw_target:
                            os.close(parent_fd)
                            tf.close()
                            return False
                    except OSError:
                        os.close(parent_fd)
                        tf.close()
                        return False
            
            elif member_type == 'hardlink':
                # Validate target exists on disk and is a regular file (not symlink)
                link_target = os.path.normpath(os.path.join(base, m.linkname))
                
                # Verify link_target is inside base
                if not link_target.startswith(base_prefix):
                    os.close(parent_fd)
                    tf.close()
                    return False
                
                # Check target exists and is regular file using lstat-equivalent
                # We need to check without following symlinks
                target_parent_fd, target_final_name = verify_and_ensure_parent_dir(link_target)
                if target_parent_fd is None:
                    os.close(parent_fd)
                    tf.close()
                    return False
                
                try:
                    try:
                        target_fd = os.open(target_final_name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=target_parent_fd)
                    except OSError:
                        os.close(target_parent_fd)
                        os.close(parent_fd)
                        tf.close()
                        return False
                    
                    try:
                        st = os.fstat(target_fd)
                        if not os.path.isfile(st.st_mode) or os.path.islink(st.st_mode):
                            # Note: os.path.islink on stat result requires lstat; fstat follows symlinks
                            # But we opened with O_NOFOLLOW, so if it's a symlink, open would fail on some systems
                            # Actually, O_NOFOLLOW on open fails if the final component is a symlink
                            # So if open succeeded, it's not a symlink
                            pass
                    finally:
                        os.close(target_fd)
                finally:
                    os.close(target_parent_fd)
                
                # Create hard link
                # Use linkat with AT_SYMLINK_FOLLOW not set to not follow symlinks
                try:
                    os.link(link_target, os.path.join(member_path), follow_symlinks=False)
                except (TypeError, AttributeError):
                    # Python < 3.10 or no follow_symlinks support, use alternative
                    # On Linux, link() doesn't follow symlinks by default
                    try:
                        # Try using linkat via libc or fallback
                        os.link(link_target, member_path)
                    except OSError:
                        os.close(parent_fd)
                        tf.close()
                        return False
                except OSError:
                    # Try direct path-based link
                    try:
                        os.link(link_target, member_path)
                    except OSError:
                        os.close(parent_fd)
                        tf.close()
                        return False
        
        finally:
            os.close(parent_fd)
    
    tf.close()
    return True
