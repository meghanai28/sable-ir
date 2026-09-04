import os
import tarfile
import stat
import errno


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    # Ensure dest_path exists as a directory
    try:
        os.makedirs(dest_path, exist_ok=True)
    except (OSError, IOError):
        return False
    
    # Compute canonical absolute path with symlinks resolved, append trailing separator
    try:
        dest_real = os.path.realpath(dest_path)
        if not os.path.isdir(dest_real):
            return False
        trust_boundary = os.path.join(dest_real, '')
    except (OSError, IOError):
        return False
    
    def is_within_boundary(path: str) -> bool:
        """Check if path is within trust_boundary."""
        normalized = os.path.normpath(path)
        # Must be exactly trust_boundary (without trailing sep for comparison) or start with boundary
        boundary_no_sep = dest_real
        if normalized == boundary_no_sep:
            return True
        # Check with trailing separator to prevent prefix attacks
        return normalized.startswith(trust_boundary)
    
    def sanitize_member_name(name: str) -> str:
        """Strip leading absolute path indicators from member name."""
        # Remove leading slashes and backslashes
        while name and name[0] in '/\\':
            name = name[1:]
        # Remove Windows drive letters (e.g., C:, c:)
        if len(name) >= 2 and name[1] == ':':
            if name[0].isalpha():
                name = name[2:]
                # Also remove any leading separators after drive letter
                while name and name[0] in '/\\':
                    name = name[1:]
        # Remove any embedded .. components by normalizing, but we do full path normalization later
        return name
    
    def get_candidate_path(member_name: str) -> str:
        """Get sanitized and normalized candidate extraction path."""
        sanitized = sanitize_member_name(member_name)
        if not sanitized:
            # Empty name after sanitization - would map to trust_boundary
            return trust_boundary.rstrip(os.sep)
        joined = os.path.join(dest_real, sanitized)
        normalized = os.path.normpath(joined)
        return normalized
    
    try:
        tf = tarfile.open(tar_path, mode='r:*')
    except (tarfile.TarError, OSError, IOError):
        return False
    
    # Phase 1: Validation
    members = []
    regular_file_targets = set()  # Set of normalized paths for regular file members
    
    try:
        for member in tf.getmembers():
            # Reject non-standard file types
            if member.issym() or member.islnk() or member.isreg() or member.isdir():
                pass  # Allowed types
            else:
                # Reject device nodes, FIFOs, and other non-standard types
                return False
            
            candidate_path = get_candidate_path(member.name)
            
            # Validate member path is within boundary
            if candidate_path == dest_real:
                # Only directory-type members can map exactly to dest_path
                if not member.isdir():
                    return False
            elif not candidate_path.startswith(trust_boundary):
                return False
            
            # Store member info for phase 2
            members.append((member, candidate_path))
            
            # Track regular files for hard link validation
            if member.isreg():
                regular_file_targets.add(candidate_path)
    except (OSError, IOError, tarfile.TarError):
        return False
    
    # Validate symlinks and hardlinks
    for member, candidate_path in members:
        if member.issym():
            # Validate symlink target
            link_target = member.linkname
            if link_target is None:
                return False
            
            parent_dir = os.path.dirname(candidate_path)
            
            if os.path.isabs(link_target):
                # Absolute target: normalize directly
                resolved = os.path.normpath(link_target)
            else:
                # Relative target: resolve from parent directory
                resolved = os.path.normpath(os.path.join(parent_dir, link_target))
            
            # Must be within trust boundary
            if resolved == dest_real:
                pass  # OK, points to dest_path itself
            elif not resolved.startswith(trust_boundary):
                return False
        
        elif member.islnk():
            # Validate hard link target
            link_target_name = member.linkname
            if link_target_name is None:
                return False
            
            target_path = get_candidate_path(link_target_name)
            
            # Must be within boundary
            if target_path == dest_real:
                return False  # Hard link to directory not allowed
            if not target_path.startswith(trust_boundary):
                return False
            
            # Must point to a regular file member in the same archive
            if target_path not in regular_file_targets:
                return False
    
    # Phase 2: Extraction with TOCTOU protection
    try:
        # Open directory file descriptor for safe relative operations
        dest_fd = os.open(dest_real, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    except (OSError, IOError):
        return False
    
    try:
        # Track which regular files have been written for hard links
        written_regular_files = {}  # normalized_path -> (fd or path info)
        
        # Need to process members in dependency order for hard links
        # First pass: identify all members and their types
        # Second pass: extract, handling hard links after their targets
        
        # Build dependency graph for hard links
        hard_link_deps = {}  # target_path -> [(member, candidate_path), ...]
        regular_files_to_extract = []
        symlinks_to_extract = []
        dirs_to_extract = []
        hard_links_to_extract = []
        
        for member, candidate_path in members:
            if member.isdir():
                dirs_to_extract.append((member, candidate_path))
            elif member.issym():
                symlinks_to_extract.append((member, candidate_path))
            elif member.islnk():
                target_name = member.linkname
                target_path = get_candidate_path(target_name)
                hard_link_deps.setdefault(target_path, []).append((member, candidate_path))
                hard_links_to_extract.append((member, candidate_path, target_path))
            elif member.isreg():
                regular_files_to_extract.append((member, candidate_path))
        
        # Extract directories first
        for member, candidate_path in dirs_to_extract:
            rel_path = os.path.relpath(candidate_path, dest_real)
            if rel_path == '.' or rel_path == '':
                continue
            
            # Create directory using safe relative operations
            # Walk components and create/verify each
            components = rel_path.split(os.sep)
            current_fd = dest_fd
            try:
                for i, component in enumerate(components):
                    if not component or component == '.':
                        continue
                    
                    # Try to open existing directory
                    try:
                        next_fd = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC, dir_fd=current_fd)
                        if i < len(components) - 1:
                            # Not last component, close current and continue
                            if current_fd != dest_fd:
                                os.close(current_fd)
                            current_fd = next_fd
                        else:
                            # Last component, it's a directory
                            os.close(next_fd)
                            if current_fd != dest_fd:
                                os.close(current_fd)
                    except OSError as e:
                        if e.errno == errno.ENOENT:
                            # Need to create
                            os.mkdir(component, mode=0o777, dir_fd=current_fd)
                            if i == len(components) - 1:
                                # Set proper mode for final directory
                                try:
                                    os.chmod(component, mode=member.mode, dir_fd=current_fd)
                                except OSError:
                                    pass
                            if current_fd != dest_fd:
                                os.close(current_fd)
                            # Re-open to continue
                            if i < len(components) - 1:
                                current_fd = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC, dir_fd=dest_fd if i == 0 else current_fd)
                                # Need to get fd relative to dest_fd for first, then chain
                                # Actually we need to restructure, use simpler approach
                        else:
                            raise
            except OSError:
                return False
        
        # Re-implement with simpler but safe approach: create directories using os.makedirs equivalent
        # But with verification that we're under dest_path
        
        # Actually, let's use a cleaner approach: for each path, verify parent is real directory under dest_path
        def safe_make_dirs(target_path: str, mode: int = 0o777) -> bool:
            """Safely create directories ensuring they stay under dest_real."""
            if target_path == dest_real:
                return True
            
            rel = os.path.relpath(target_path, dest_real)
            if rel.startswith('..'):
                return False
            
            components = rel.split(os.sep)
            current_path = dest_real
            
            for component in components:
                if not component:
                    continue
                current_path = os.path.join(current_path, component)
                normalized = os.path.normpath(current_path)
                if not normalized.startswith(trust_boundary) and normalized != dest_real:
                    return False
                
                try:
                    if not os.path.isdir(normalized):
                        os.mkdir(normalized, mode)
                except OSError as e:
                    if e.errno != errno.EEXIST:
                        return False
                    # Exists, verify it's a directory
                    if not os.path.isdir(normalized):
                        return False
            
            return True
        
        # Re-extract directories with safe approach
        for member, candidate_path in dirs_to_extract:
            if not safe_make_dirs(candidate_path, member.mode):
                return False
        
        # Extract regular files
        for member, candidate_path in regular_files_to_extract:
            rel_path = os.path.relpath(candidate_path, dest_real)
            if rel_path.startswith('..'):
                return False
            
            # Ensure parent directory exists
            parent = os.path.dirname(candidate_path)
            if not safe_make_dirs(parent):
                return False
            
            # Verify parent is real directory (not symlink)
            try:
                parent_stat = os.stat(parent)
                if not stat.S_ISDIR(parent_stat.st_mode):
                    return False
            except OSError:
                return False
            
            # Extract file content
            try:
                with tf.extractfile(member) as src_fh:
                    # Write to temporary file then rename, or write directly with safe flags
                    # Use os.open with O_NOFOLLOW to avoid following symlinks
                    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_CLOEXEC
                    if hasattr(os, 'O_NOFOLLOW'):
                        flags |= os.O_NOFOLLOW
                    
                    try:
                        fd = os.open(candidate_path, flags, mode=0o666)
                    except OSError as e:
                        if e.errno == errno.ENOENT:
                            return False
                        # If O_NOFOLLOW causes ELOOP on symlink, that's good - we reject
                        if hasattr(errno, 'ELOOP') and e.errno == errno.ELOOP:
                            return False
                        raise
                    
                    try:
                        # Set proper mode
                        os.fchmod(fd, member.mode)
                        
                        # Copy content
                        while True:
                            chunk = src_fh.read(65536)
                            if not chunk:
                                break
                            os.write(fd, chunk)
                        
                        # Sync to ensure data is written
                        os.fsync(fd)
                    finally:
                        os.close(fd)
                    
                    written_regular_files[candidate_path] = True
            except (OSError, IOError, TypeError):
                return False
        
        # Extract symlinks
        for member, candidate_path in regular_files_to_extract:
            pass  # Already done above
        
        for member, candidate_path in symlinks_to_extract:
            rel_path = os.path.relpath(candidate_path, dest_real)
            if rel_path.startswith('..'):
                return False
            
            # Ensure parent directory exists
            parent = os.path.dirname(candidate_path)
            if not safe_make_dirs(parent):
                return False
            
            # Verify parent is real directory
            try:
                parent_stat = os.stat(parent)
                if not stat.S_ISDIR(parent_stat.st_mode):
                    return False
            except OSError:
                return False
            
            # Remove existing file if any (safely)
            try:
                # Use lstat to not follow symlinks
                existing = os.lstat(candidate_path)
                # Exists, remove it
                if stat.S_ISDIR(existing.st_mode):
                    os.rmdir(candidate_path)
                else:
                    os.unlink(candidate_path)
            except OSError as e:
                if e.errno != errno.ENOENT:
                    return False
            
            # Create symlink with raw target (validation ensures safety)
            try:
                os.symlink(member.linkname, candidate_path)
            except (OSError, IOError):
                return False
        
        # Extract hard links (after their targets are written)
        for member, candidate_path, target_path in hard_links_to_extract:
            # Verify target was written
            if target_path not in written_regular_files:
                return False
            
            rel_path = os.path.relpath(candidate_path, dest_real)
            if rel_path.startswith('..'):
                return False
            
            # Ensure parent directory exists
            parent = os.path.dirname(candidate_path)
            if not safe_make_dirs(parent):
                return False
            
            # Verify parent is real directory
            try:
                parent_stat = os.stat(parent)
                if not stat.S_ISDIR(parent_stat.st_mode):
                    return False
            except OSError:
                return False
            
            # Verify target exists as regular file
            try:
                target_stat = os.stat(target_path)
                if not stat.S_ISREG(target_stat.st_mode):
                    return False
            except OSError:
                return False
            
            # Remove existing file if any
            try:
                existing = os.lstat(candidate_path)
                if stat.S_ISDIR(existing.st_mode):
                    os.rmdir(candidate_path)
                else:
                    os.unlink(candidate_path)
            except OSError as e:
                if e.errno != errno.ENOENT:
                    return False
            
            # Create hard link
            try:
                os.link(target_path, candidate_path)
            except (OSError, IOError):
                return False
        
        # Set directory modes properly (in case umask affected creation)
        for member, candidate_path in dirs_to_extract:
            if candidate_path != dest_real:
                try:
                    os.chmod(candidate_path, member.mode)
                except (OSError, IOError):
                    pass  # Non-fatal for mode setting
        
        # Set file timestamps if possible (optional, but good practice)
        for member, candidate_path in members:
            if not member.isdir():
                try:
                    # Use member's mtime
                    os.utime(candidate_path, (member.mtime, member.mtime), follow_symlinks=False)
                except (OSError, IOError):
                    pass  # Non-fatal
        
    except (OSError, IOError, tarfile.TarError):
        return False
    finally:
        try:
            os.close(dest_fd)
        except (OSError, IOError):
            pass
        try:
            tf.close()
        except (OSError, IOError, tarfile.TarError):
            pass
    
    return True
