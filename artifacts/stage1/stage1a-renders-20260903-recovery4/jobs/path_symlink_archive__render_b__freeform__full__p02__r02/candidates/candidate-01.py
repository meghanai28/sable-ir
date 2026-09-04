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
        # Ensure trailing separator for prefix matching
        if not trust_boundary.endswith(os.sep):
            trust_boundary = trust_boundary + os.sep
    except (OSError, ValueError):
        return False

    def _is_within_boundary(candidate_path: str, allow_exact: bool = False) -> bool:
        """Check if candidate_path is within trust_boundary."""
        norm = os.path.normpath(candidate_path)
        # Handle case where normpath strips trailing sep
        if norm != trust_boundary.rstrip(os.sep) and not norm.endswith(os.sep):
            norm = norm + os.sep
        boundary_check = trust_boundary
        if norm == boundary_check.rstrip(os.sep) or norm == boundary_check.rstrip(os.sep) + os.sep:
            return allow_exact
        # Must start with trust_boundary as prefix
        prefix = trust_boundary
        if not norm.startswith(prefix):
            # Also check without trailing sep for exact match
            if norm.rstrip(os.sep) == boundary_check.rstrip(os.sep):
                return allow_exact
            return False
        return True

    def _sanitize_member_name(name: str) -> str:
        """Strip leading absolute path indicators from member name."""
        if not name:
            return name
        # Strip leading slashes and backslashes
        while name and name[0] in '/\\':
            name = name[1:]
        # Strip Windows drive letters (e.g., C:, c:)
        if len(name) >= 2 and name[1] == ':':
            if name[0].isalpha():
                name = name[2:]
                # Strip any leading separators after drive letter
                while name and name[0] in '/\\':
                    name = name[1:]
        # Continue stripping leading slashes and backslashes
        while name and name[0] in '/\\':
            name = name[1:]
        return name

    def _get_candidate_path(member_name: str) -> str:
        """Get validated candidate extraction path for a member name."""
        sanitized = _sanitize_member_name(member_name)
        if sanitized == '':
            # Empty name after sanitization - would map to trust boundary
            return trust_boundary.rstrip(os.sep)
        # Join with trust boundary (without trailing sep for join)
        base = trust_boundary.rstrip(os.sep)
        joined = os.path.join(base, sanitized)
        normalized = os.path.normpath(joined)
        return normalized

    # Phase 1: Validation pass
    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
            
            # Track regular file members for hard link validation
            regular_file_members = set()  # Set of normalized paths that are regular files
            
            # First pass: validate all member paths and collect regular files
            validated_members = []  # List of (member, candidate_path, member_type_info)
            
            for member in members:
                # Skip the end-of-archive marker
                if member.name == '' or member.isspecial() and not (member.issym() or member.islnk()):
                    pass  # Will check types below
                
                candidate_path = _get_candidate_path(member.name)
                
                # Determine if this is a directory member
                is_dir = member.isdir() or member.name.endswith('/')
                
                # Validate path is within boundary
                if not _is_within_boundary(candidate_path, allow_exact=is_dir):
                    return False
                
                # Check for path traversal via dot-dot components
                # Re-sanitize and verify no escape
                sanitized = _sanitize_member_name(member.name)
                if '..' in sanitized.split('/'):
                    # Additional check: normpath should have resolved this, but verify
                    pass  # normpath in _get_candidate_path handles this
                
                # Reject non-standard file types (devices, FIFOs, etc.)
                if member.isdev() or member.isfifo() or (not member.isfile() and not member.isdir() 
                                                          and not member.issym() and not member.islnk()):
                    return False
                
                # For symlinks: validate target
                if member.issym():
                    link_target = member.linkname
                    if link_target is None:
                        return False
                    
                    # Compute where symlink would resolve
                    if os.path.isabs(link_target):
                        # Absolute target: normalize directly
                        # Sanitize the target similar to member names
                        sanitized_target = _sanitize_member_name(link_target)
                        if sanitized_target == '':
                            resolved = trust_boundary.rstrip(os.sep)
                        else:
                            resolved = os.path.normpath(os.path.join(trust_boundary.rstrip(os.sep), sanitized_target))
                    else:
                        # Relative target: resolve from parent of symlink
                        parent_dir = os.path.dirname(candidate_path)
                        resolved = os.path.normpath(os.path.join(parent_dir, link_target))
                    
                    if not _is_within_boundary(resolved, allow_exact=False):
                        return False
                
                # For hard links: validate target and record for later
                if member.islnk():
                    link_target_name = member.linkname
                    if link_target_name is None:
                        return False
                    
                    sanitized_target = _sanitize_member_name(link_target_name)
                    if sanitized_target == '':
                        target_path = trust_boundary.rstrip(os.sep)
                    else:
                        target_path = os.path.normpath(os.path.join(trust_boundary.rstrip(os.sep), sanitized_target))
                    
                    if not _is_within_boundary(target_path, allow_exact=False):
                        return False
                    
                    # Must point to a regular file member in the same archive
                    # We'll verify this in second pass after collecting all regular files
                
                validated_members.append((member, candidate_path))
                
                # Preliminary: mark as regular file if applicable
                if member.isfile():
                    regular_file_members.add(os.path.normpath(candidate_path))
            
            # Second pass: validate hard links against collected regular files
            for member, candidate_path in validated_members:
                if member.islnk():
                    link_target_name = member.linkname
                    sanitized_target = _sanitize_member_name(link_target_name)
                    if sanitized_target == '':
                        target_path = trust_boundary.rstrip(os.sep)
                    else:
                        target_path = os.path.normpath(os.path.join(trust_boundary.rstrip(os.sep), sanitized_target))
                    
                    if os.path.normpath(target_path) not in regular_file_members:
                        return False
            
            # Phase 2: Extraction
            # Open dest_path directory file descriptor for safe relative operations
            try:
                dest_fd = os.open(dest_path, os.O_RDONLY | os.O_DIRECTORY)
            except OSError:
                return False
            
            try:
                # Track created directories and written regular files for hard links
                created_dirs = set()
                written_regular_files = {}  # normalized_path -> actual path for hard linking
                
                for member, candidate_path in validated_members:
                    norm_candidate = os.path.normpath(candidate_path)
                    
                    # Get path relative to dest_path for safe creation
                    rel_path = os.path.relpath(candidate_path, trust_boundary.rstrip(os.sep))
                    if rel_path == '.':
                        rel_path = ''
                    
                    if member.isdir() or member.name.endswith('/'):
                        # Create directory
                        if rel_path:
                            try:
                                # Build path safely, checking each component
                                current_path = trust_boundary.rstrip(os.sep)
                                parts = rel_path.split(os.sep)
                                for part in parts:
                                    if not part or part == '.':
                                        continue
                                    if part == '..':
                                        return False
                                    current_path = os.path.join(current_path, part)
                                    norm_current = os.path.normpath(current_path)
                                    if not _is_within_boundary(norm_current, allow_exact=True):
                                        return False
                                    # Verify it's a real directory or can be created
                                    if os.path.exists(norm_current):
                                        if not os.path.isdir(norm_current):
                                            return False
                                    else:
                                        os.mkdir(norm_current)
                                    created_dirs.add(norm_current)
                            except OSError:
                                return False
                    elif member.isfile():
                        # Extract regular file
                        if not rel_path:
                            return False  # Can't extract file to root
                        
                        # Ensure parent directory exists and is safe
                        parent = os.path.dirname(candidate_path)
                        norm_parent = os.path.normpath(parent)
                        if not _is_within_boundary(norm_parent, allow_exact=True):
                            return False
                        
                        # Verify parent is a real directory (not symlink)
                        try:
                            parent_stat = os.lstat(norm_parent)
                            if not stat.S_ISDIR(parent_stat.st_mode):
                                # Try to create if doesn't exist
                                if not os.path.isdir(norm_parent):
                                    os.makedirs(norm_parent, exist_ok=True)
                                    parent_stat = os.lstat(norm_parent)
                                    if not stat.S_ISDIR(parent_stat.st_mode):
                                        return False
                        except OSError:
                            return False
                        
                        # Extract file content
                        try:
                            # Open for writing without following symlinks
                            # Use os.open with O_NOFOLLOW if available, or check after
                            flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_EXCL
                            try:
                                fd = os.open(candidate_path, flags, 0o666)
                            except FileExistsError:
                                # Remove and retry, or check if it's safe
                                try:
                                    st = os.lstat(candidate_path)
                                    if stat.S_ISDIR(st.st_mode):
                                        return False
                                    os.unlink(candidate_path)
                                    fd = os.open(candidate_path, flags, 0o666)
                                except OSError:
                                    return False
                            
                            try:
                                # Copy content from tar
                                fobj = tf.extractfile(member)
                                if fobj is None:
                                    os.close(fd)
                                    return False
                                try:
                                    while True:
                                        chunk = fobj.read(65536)
                                        if not chunk:
                                            break
                                        os.write(fd, chunk)
                                finally:
                                    fobj.close()
                            finally:
                                os.close(fd)
                            
                            # Set permissions
                            os.chmod(candidate_path, member.mode & 0o7777)
                            
                            written_regular_files[norm_candidate] = candidate_path
                            
                        except OSError:
                            return False
                    
                    elif member.issym():
                        # Create symbolic link
                        if not rel_path:
                            return False
                        
                        # Verify parent directory is safe
                        parent = os.path.dirname(candidate_path)
                        norm_parent = os.path.normpath(parent)
                        if not _is_within_boundary(norm_parent, allow_exact=True):
                            return False
                        
                        try:
                            parent_stat = os.lstat(norm_parent)
                            if not stat.S_ISDIR(parent_stat.st_mode):
                                return False
                        except OSError:
                            return False
                        
                        # Remove existing file if present
                        try:
                            if os.path.lexists(candidate_path):
                                os.unlink(candidate_path)
                        except OSError:
                            pass
                        
                        try:
                            os.symlink(member.linkname, candidate_path)
                        except OSError:
                            return False
                    
                    elif member.islnk():
                        # Create hard link
                        if not rel_path:
                            return False
                        
                        # Verify parent directory is safe
                        parent = os.path.dirname(candidate_path)
                        norm_parent = os.path.normpath(parent)
                        if not _is_within_boundary(norm_parent, allow_exact=True):
                            return False
                        
                        try:
                            parent_stat = os.lstat(norm_parent)
                            if not stat.S_ISDIR(parent_stat.st_mode):
                                return False
                        except OSError:
                            return False
                        
                        # Get target path
                        link_target_name = member.linkname
                        sanitized_target = _sanitize_member_name(link_target_name)
                        if sanitized_target == '':
                            target_path = trust_boundary.rstrip(os.sep)
                        else:
                            target_path = os.path.normpath(os.path.join(trust_boundary.rstrip(os.sep), sanitized_target))
                        
                        norm_target = os.path.normpath(target_path)
                        
                        # Verify target has been written
                        if norm_target not in written_regular_files:
                            return False
                        
                        actual_target = written_regular_files[norm_target]
                        
                        # Remove existing file if present
                        try:
                            if os.path.lexists(candidate_path):
                                os.unlink(candidate_path)
                        except OSError:
                            pass
                        
                        try:
                            os.link(actual_target, candidate_path)
                        except OSError:
                            return False
                
                return True
                
            finally:
                try:
                    os.close(dest_fd)
                except OSError:
                    pass
                    
    except (tarfile.TarError, OSError, ValueError):
        return False
    
    return False
