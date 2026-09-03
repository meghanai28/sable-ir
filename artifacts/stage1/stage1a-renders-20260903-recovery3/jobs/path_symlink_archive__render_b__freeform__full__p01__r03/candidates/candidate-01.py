import os
import tarfile
import errno
import fcntl

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    # Ensure dest_path exists as a directory and resolve to canonical absolute path
    try:
        os.makedirs(dest_path, exist_ok=True)
        canonical_dest = os.path.realpath(dest_path)
        if not os.path.isdir(canonical_dest):
            return False
    except (OSError, ValueError):
        return False
    
    # Ensure canonical_dest ends with separator for reliable prefix checking
    canonical_dest_prefix = canonical_dest + os.sep
    
    # Open tar and enumerate all members for validation
    try:
        tar = tarfile.open(tar_path, 'r:*')
    except (tarfile.TarError, OSError, IOError):
        return False
    
    # First pass: validate all members without extracting
    validated_members = []
    
    for member in tar.getmembers():
        # Reject absolute member names
        if os.path.isabs(member.name):
            tar.close()
            return False
        
        # Compute normalized absolute extraction path
        member_path = os.path.normpath(os.path.join(canonical_dest, member.name))
        
        # Reject if not strictly beneath canonical_dest
        if not (member_path + os.sep).startswith(canonical_dest_prefix) and member_path != canonical_dest:
            tar.close()
            return False
        
        # Validate based on member type
        if member.issym() or member.islnk():
            # Symbolic link
            if member.issym():
                link_target = member.linkname
                # Normalize link target
                if os.path.isabs(link_target):
                    normalized_target = os.path.normpath(link_target)
                else:
                    parent_dir = os.path.dirname(member_path)
                    normalized_target = os.path.normpath(os.path.join(parent_dir, link_target))
                
                # Reject if not strictly within canonical_dest
                if not (normalized_target + os.sep).startswith(canonical_dest_prefix) and normalized_target != canonical_dest:
                    tar.close()
                    return False
            
            # Hard link
            elif member.islnk():
                # Target is another archive member name
                if os.path.isabs(member.linkname):
                    tar.close()
                    return False
                
                link_target_path = os.path.normpath(os.path.join(canonical_dest, member.linkname))
                
                # Reject if not strictly beneath canonical_dest
                if not (link_target_path + os.sep).startswith(canonical_dest_prefix) and link_target_path != canonical_dest:
                    tar.close()
                    return False
                
                # Reject if references existing file outside dest_path
                try:
                    existing_real = os.path.realpath(link_target_path)
                    if os.path.exists(existing_real):
                        if not (existing_real + os.sep).startswith(canonical_dest_prefix) and existing_real != canonical_dest:
                            tar.close()
                            return False
                except (OSError, ValueError):
                    tar.close()
                    return False
        
        elif member.isdir():
            pass  # Directory is fine
        
        elif member.isfile() or member.isreg():
            pass  # Regular file is fine
        
        else:
            # Reject device nodes, FIFOs, and other unsupported types
            tar.close()
            return False
        
        validated_members.append((member, member_path))
    
    # All members validated, now extract
    # Open directory file descriptor for dest_path for path-traversal-resistant operations
    try:
        dest_fd = os.open(canonical_dest, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    except OSError:
        tar.close()
        return False
    
    try:
        # Process members in order (parents before children typically)
        for member, member_path in validated_members:
            # Compute relative path components from canonical_dest
            rel_path = os.path.relpath(member_path, canonical_dest)
            if rel_path == '.':
                continue  # Skip if it's the dest directory itself
            
            path_parts = rel_path.split(os.sep)
            
            # Navigate/create intermediate directories
            current_fd = dest_fd
            
            try:
                # Process all but the last component as directories
                for i, part in enumerate(path_parts[:-1]):
                    try:
                        # Try to open existing directory without following symlinks
                        next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=current_fd)
                        if current_fd != dest_fd:
                            os.close(current_fd)
                        current_fd = next_fd
                    except OSError as e:
                        if e.errno == errno.ENOTDIR or e.errno == errno.ELOOP:
                            # Not a directory or is a symlink, fail
                            if current_fd != dest_fd:
                                os.close(current_fd)
                            return False
                        elif e.errno == errno.ENOENT:
                            # Doesn't exist, create directory
                            try:
                                os.mkdir(part, dir_fd=current_fd)
                                next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=current_fd)
                                if current_fd != dest_fd:
                                    os.close(current_fd)
                                current_fd = next_fd
                            except OSError:
                                if current_fd != dest_fd:
                                    os.close(current_fd)
                                return False
                        else:
                            if current_fd != dest_fd:
                                os.close(current_fd)
                            return False
                
                # Handle the final component
                final_name = path_parts[-1]
                
                if member.isdir():
                    try:
                        os.mkdir(final_name, mode=member.mode, dir_fd=current_fd)
                    except OSError as e:
                        if e.errno != errno.EEXIST:
                            if current_fd != dest_fd:
                                os.close(current_fd)
                            return False
                    if current_fd != dest_fd:
                        os.close(current_fd)
                
                elif member.isfile() or member.isreg():
                    # Extract file contents
                    try:
                        file_fd = os.open(final_name, os.O_CREAT | os.O_WRONLY | os.O_NOFOLLOW | os.O_EXCL, mode=member.mode, dir_fd=current_fd)
                    except OSError:
                        if current_fd != dest_fd:
                            os.close(current_fd)
                        return False
                    
                    try:
                        fobj = tar.extractfile(member)
                        if fobj is None:
                            os.close(file_fd)
                            if current_fd != dest_fd:
                                os.close(current_fd)
                            return False
                        
                        while True:
                            chunk = fobj.read(65536)
                            if not chunk:
                                break
                            os.write(file_fd, chunk)
                        
                        fobj.close()
                    except (OSError, IOError):
                        os.close(file_fd)
                        if current_fd != dest_fd:
                            os.close(current_fd)
                        return False
                    
                    os.close(file_fd)
                    if current_fd != dest_fd:
                        os.close(current_fd)
                
                elif member.issym():
                    # Create symbolic link with validated target
                    link_target = member.linkname
                    try:
                        os.symlink(link_target, final_name, dir_fd=current_fd)
                    except OSError:
                        if current_fd != dest_fd:
                            os.close(current_fd)
                            return False
                    if current_fd != dest_fd:
                        os.close(current_fd)
                
                elif member.islnk():
                    # Hard link - need source path relative to dest_fd
                    source_rel = os.path.relpath(os.path.normpath(os.path.join(canonical_dest, member.linkname)), canonical_dest)
                    source_parts = source_rel.split(os.sep)
                    
                    # Build source path string relative to current directory context
                    # We need to use linkat with both dir_fds
                    # For simplicity, open source relative to dest_fd
                    try:
                        # Navigate to source parent
                        source_fd = dest_fd
                        for part in source_parts[:-1]:
                            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=source_fd)
                            if source_fd != dest_fd:
                                os.close(source_fd)
                            source_fd = next_fd
                        
                        source_name = source_parts[-1]
                        os.link(source_name, final_name, src_dir_fd=source_fd, dst_dir_fd=current_fd, follow_symlinks=False)
                        
                        if source_fd != dest_fd:
                            os.close(source_fd)
                        if current_fd != dest_fd:
                            os.close(current_fd)
                    except OSError:
                        if source_fd != dest_fd and 'source_fd' in dir() and source_fd != current_fd:
                            try:
                                os.close(source_fd)
                            except:
                                pass
                        if current_fd != dest_fd:
                            os.close(current_fd)
                        return False
            
            except Exception:
                if 'current_fd' in dir() and current_fd != dest_fd:
                    try:
                        os.close(current_fd)
                    except:
                        pass
                return False
    
    finally:
        os.close(dest_fd)
    
    tar.close()
    return True
