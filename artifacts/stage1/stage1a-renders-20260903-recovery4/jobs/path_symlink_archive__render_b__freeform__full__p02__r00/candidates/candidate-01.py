import os
import tarfile
import stat
import errno

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    # Phase 0: Establish trust boundary
    try:
        os.makedirs(dest_path, exist_ok=True)
        if not os.path.isdir(dest_path):
            return False
        trust_boundary = os.path.realpath(dest_path)
        if not os.path.isdir(trust_boundary):
            return False
        # Append trailing separator for prefix check
        if not trust_boundary.endswith(os.sep):
            trust_boundary = trust_boundary + os.sep
    except (OSError, ValueError):
        return False

    def is_within_boundary(path: str) -> bool:
        """Check if path is within trust_boundary. Directory members may equal trust_boundary (without trailing sep)."""
        # For prefix check, ensure path has trailing sep if it's a directory
        if path == trust_boundary.rstrip(os.sep):
            return True
        if not path.endswith(os.sep):
            path_with_sep = path + os.sep
        else:
            path_with_sep = path
        if path_with_sep.startswith(trust_boundary):
            return True
        return False

    def sanitize_member_name(name: str) -> str:
        """Strip leading absolute path indicators including slashes, backslashes, and Windows drive letters."""
        # Remove leading slashes and backslashes
        while name and name[0] in '/\\':
            name = name[1:]
        # Remove Windows drive letters like C: or c:
        if len(name) >= 2 and name[1] == ':':
            if name[0].isalpha():
                name = name[2:]
                # Remove any leading separators after drive letter
                while name and name[0] in '/\\':
                    name = name[1:]
        # Remove any remaining leading path separators
        while name and name[0] in '/\\':
            name = name[1:]
        return name

    def normalize_path(path: str) -> str:
        """Normalize path, resolving ., .., and redundant separators."""
        return os.path.normpath(path)

    def get_candidate_path(member_name: str) -> str:
        """Get sanitized and normalized candidate extraction path."""
        sanitized = sanitize_member_name(member_name)
        if not sanitized:
            # Empty name after sanitization - would map to trust_boundary
            return trust_boundary.rstrip(os.sep)
        joined = os.path.join(trust_boundary.rstrip(os.sep), sanitized)
        normalized = normalize_path(joined)
        return normalized

    # Phase 1: Validation pass
    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
            
            # Collect validated info
            validated_members = []  # list of (member, candidate_path)
            regular_file_paths = set()  # set of normalized paths of regular files in archive
            symlink_targets = {}  # member_name -> (candidate_path, raw_target, resolved_target)
            hardlink_targets = {}  # member_name -> (candidate_path, raw_target, resolved_target)
            
            # First pass: collect all regular file paths and validate member paths
            for member in members:
                candidate = get_candidate_path(member.name)
                
                # Check boundary for member path
                if member.isdir():
                    # Directory can be exactly trust_boundary or within it
                    if candidate != trust_boundary.rstrip(os.sep) and not is_within_boundary(candidate):
                        return False
                else:
                    # Non-directory must be strictly within boundary
                    if candidate == trust_boundary.rstrip(os.sep):
                        return False
                    if not is_within_boundary(candidate):
                        return False
                
                # Reject non-standard types
                if member.issym():
                    pass  # handled below
                elif member.islnk():
                    pass  # handled below
                elif member.isdir():
                    pass  # OK
                elif member.isfile() or member.isreg():
                    regular_file_paths.add(candidate)
                else:
                    # Device node, FIFO, or other non-standard
                    return False
                
                validated_members.append((member, candidate))
            
            # Second pass: validate symlinks and hardlinks, and collect targets
            for member, candidate in validated_members:
                if member.issym():
                    raw_target = member.linkname
                    
                    # Compute resolved target
                    if os.path.isabs(raw_target):
                        # Absolute target: sanitize and normalize
                        sanitized_target = sanitize_member_name(raw_target)
                        if not sanitized_target:
                            return False
                        resolved = normalize_path(os.path.join(trust_boundary.rstrip(os.sep), sanitized_target))
                    else:
                        # Relative target: resolve from parent of candidate
                        parent = os.path.dirname(candidate)
                        resolved = normalize_path(os.path.join(parent, raw_target))
                    
                    # Check resolved target is within boundary
                    if not is_within_boundary(resolved):
                        return False
                    
                    symlink_targets[member.name] = (candidate, raw_target, resolved)
                    
                elif member.islnk():
                    raw_target = member.linkname
                    
                    # Sanitize hardlink target name
                    sanitized_target = sanitize_member_name(raw_target)
                    if not sanitized_target:
                        return False
                    resolved = normalize_path(os.path.join(trust_boundary.rstrip(os.sep), sanitized_target))
                    
                    # Check resolved target is within boundary
                    if not is_within_boundary(resolved):
                        return False
                    
                    # Check target corresponds to a regular file member in this archive
                    if resolved not in regular_file_paths:
                        return False
                    
                    hardlink_targets[member.name] = (candidate, raw_target, resolved)
            
            # Phase 2: Extraction with TOCTOU protection
            # Open dest_path directory file descriptor for safe relative operations
            try:
                dest_fd = os.open(dest_path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
            except (OSError, IOError):
                return False
            
            try:
                # Track created directories and written regular files
                created_dirs = set()
                written_regular_files = set()  # normalized paths
                
                def safe_makedirs(target_path: str) -> bool:
                    """Create directory and all parents safely."""
                    # Need to create relative to dest_fd
                    # We build path components and verify each step
                    rel_path = os.path.relpath(target_path, trust_boundary.rstrip(os.sep))
                    if rel_path == '.':
                        return True
                    
                    components = rel_path.split(os.sep)
                    current_rel = ''
                    
                    for comp in components:
                        if not comp or comp == '.':
                            continue
                        current_rel = os.path.join(current_rel, comp) if current_rel else comp
                        current_abs = normalize_path(os.path.join(trust_boundary.rstrip(os.sep), current_rel))
                        
                        if current_abs in created_dirs:
                            continue
                        
                        # Check if already exists and is directory
                        try:
                            st = os.stat(current_abs, dir_fd=dest_fd, follow_symlinks=False)
                            if stat.S_ISDIR(st.st_mode):
                                created_dirs.add(current_abs)
                                continue
                            else:
                                return False
                        except FileNotFoundError:
                            pass
                        except (OSError, IOError):
                            return False
                        
                        # Create directory
                        try:
                            os.mkdir(current_abs, dir_fd=dest_fd)
                            created_dirs.add(current_abs)
                        except FileExistsError:
                            try:
                                st = os.stat(current_abs, dir_fd=dest_fd, follow_symlinks=False)
                                if stat.S_ISDIR(st.st_mode):
                                    created_dirs.add(current_abs)
                                    continue
                                else:
                                    return False
                            except (OSError, IOError):
                                return False
                        except (OSError, IOError):
                            return False
                    
                    return True
                
                def verify_parent_is_real_dir(target_path: str) -> bool:
                    """Verify parent of target_path is a real directory inside dest_path."""
                    parent = os.path.dirname(target_path)
                    if parent == trust_boundary.rstrip(os.sep):
                        return True
                    
                    try:
                        st = os.stat(parent, dir_fd=dest_fd, follow_symlinks=False)
                        if not stat.S_ISDIR(st.st_mode):
                            return False
                        # Verify it's within boundary
                        if not is_within_boundary(parent):
                            return False
                        return True
                    except (OSError, IOError):
                        return False
                
                # Extract members in archive order
                for member, candidate in validated_members:
                    if member.isdir():
                        if not safe_makedirs(candidate):
                            return False
                        # Set directory permissions if needed
                        try:
                            os.chmod(candidate, member.mode, dir_fd=dest_fd, follow_symlinks=False)
                        except (OSError, IOError):
                            pass  # Non-fatal for permissions
                            
                    elif member.isfile() or member.isreg():
                        # Ensure parent directory exists
                        if not safe_makedirs(os.path.dirname(candidate)):
                            return False
                        if not verify_parent_is_real_dir(candidate):
                            return False
                        
                        # Extract file content
                        try:
                            with tf.extractfile(member) as src:
                                if src is None:
                                    return False
                                
                                # Open output file safely
                                rel_path = os.path.relpath(candidate, trust_boundary.rstrip(os.sep))
                                flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
                                try:
                                    fd = os.open(rel_path, flags, member.mode, dir_fd=dest_fd)
                                except FileExistsError:
                                    # Remove and retry if it exists (shouldn't happen with O_EXCL)
                                    os.unlink(rel_path, dir_fd=dest_fd)
                                    fd = os.open(rel_path, flags, member.mode, dir_fd=dest_fd)
                                
                                try:
                                    while True:
                                        chunk = src.read(65536)
                                        if not chunk:
                                            break
                                        os.write(fd, chunk)
                                finally:
                                    os.close(fd)
                                
                                written_regular_files.add(candidate)
                        except (OSError, IOError, AttributeError):
                            return False
                            
                    elif member.issym():
                        # Create symlink
                        if not safe_makedirs(os.path.dirname(candidate)):
                            return False
                        if not verify_parent_is_real_dir(candidate):
                            return False
                        
                        _, raw_target, _ = symlink_targets[member.name]
                        rel_path = os.path.relpath(candidate, trust_boundary.rstrip(os.sep))
                        
                        try:
                            # Remove if exists
                            try:
                                os.unlink(rel_path, dir_fd=dest_fd)
                            except FileNotFoundError:
                                pass
                            os.symlink(raw_target, rel_path, dir_fd=dest_fd)
                        except (OSError, IOError):
                            return False
                            
                    elif member.islnk():
                        # Create hardlink
                        if not safe_makedirs(os.path.dirname(candidate)):
                            return False
                        if not verify_parent_is_real_dir(candidate):
                            return False
                        
                        _, _, resolved_target = hardlink_targets[member.name]
                        
                        # Verify target has been written
                        if resolved_target not in written_regular_files:
                            return False
                        
                        rel_path = os.path.relpath(candidate, trust_boundary.rstrip(os.sep))
                        target_rel = os.path.relpath(resolved_target, trust_boundary.rstrip(os.sep))
                        
                        try:
                            # Remove if exists
                            try:
                                os.unlink(rel_path, dir_fd=dest_fd)
                            except FileNotFoundError:
                                pass
                            os.link(target_rel, rel_path, dir_fd=dest_fd, follow_symlinks=False)
                        except (OSError, IOError):
                            return False
                
                return True
                
            finally:
                try:
                    os.close(dest_fd)
                except (OSError, IOError):
                    pass
                    
    except (tarfile.TarError, OSError, IOError, ValueError):
        return False
