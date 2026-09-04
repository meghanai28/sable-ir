import os
import tarfile
import tempfile
import shutil


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    # Step 1: Resolve dest_path to absolute, normalized, canonical directory path
    try:
        dest_path = os.path.realpath(dest_path)
    except (OSError, ValueError):
        return False
    
    if not os.path.isdir(dest_path):
        try:
            os.makedirs(dest_path, exist_ok=True)
            dest_path = os.path.realpath(dest_path)
        except (OSError, ValueError):
            return False
    
    # Ensure dest_path ends with separator for prefix checking
    dest_path_prefix = dest_path + os.sep
    
    # Step 2: Open tar archive and enumerate member list without extracting
    try:
        tar = tarfile.open(tar_path, 'r:*')
    except (tarfile.TarError, OSError, IOError):
        return False
    
    try:
        members = tar.getmembers()
    except (tarfile.TarError, OSError, IOError):
        tar.close()
        return False
    
    # Step 3: Validation pass
    validated_members = []  # List of (original_member, validated_path, validated_link_target)
    validated_paths = set()  # Set of validated extraction paths
    
    for member in members:
        # Guard (b): Validate member extraction path
        member_name = member.name
        # Reject absolute member names and names starting with parent dir traversal
        if os.path.isabs(member_name):
            tar.close()
            return False
        
        # Join with dest_path and normalize
        extraction_path = os.path.normpath(os.path.join(dest_path, member_name))
        
        # Check for path escape: must be within dest_path
        if not (extraction_path == dest_path or extraction_path.startswith(dest_path_prefix)):
            tar.close()
            return False
        
        # Reject if resolves to dest_path itself for non-directory members
        if extraction_path == dest_path and member.type not in (tarfile.DIRTYPE,):
            tar.close()
            return False
        
        # Guard (e): Reject dangerous member types
        if member.isdev() or member.isfifo():
            tar.close()
            return False
        
        # Validate link targets based on member type
        validated_link_target = None
        
        if member.issym():
            # Guard (c): Validate symbolic link target
            linkname = member.linkname
            # Get parent directory of extraction path
            parent_dir = os.path.dirname(extraction_path)
            
            if os.path.isabs(linkname):
                # Absolute linkname: treat as relative to dest_path
                normalized_target = os.path.normpath(os.path.join(dest_path, linkname.lstrip(os.sep)))
            else:
                # Relative linkname: interpret relative to parent directory
                normalized_target = os.path.normpath(os.path.join(parent_dir, linkname))
            
            # Check target is within dest_path
            if not (normalized_target == dest_path or normalized_target.startswith(dest_path_prefix)):
                tar.close()
                return False
            
            # Reject symlink that points to dest_path itself (enables upward traversal)
            if normalized_target == dest_path:
                tar.close()
                return False
            
            validated_link_target = normalized_target
            
        elif member.islnk():
            # Guard (d): Validate hard link target
            linkname = member.linkname
            
            # Compute target path by joining with dest_path and normalizing
            if os.path.isabs(linkname):
                normalized_target = os.path.normpath(os.path.join(dest_path, linkname.lstrip(os.sep)))
            else:
                normalized_target = os.path.normpath(os.path.join(dest_path, linkname))
            
            # Check target is within dest_path
            if not (normalized_target == dest_path or normalized_target.startswith(dest_path_prefix)):
                tar.close()
                return False
            
            # Hard link target must not be dest_path itself
            if normalized_target == dest_path:
                tar.close()
                return False
            
            validated_link_target = normalized_target
        
        validated_members.append((member, extraction_path, validated_link_target))
        validated_paths.add(extraction_path)
    
    # Step 4: Extraction pass
    # Deferred hard links: list of (target_path, link_path)
    deferred_hard_links = []
    
    for member, extraction_path, validated_link_target in validated_members:
        try:
            if member.isdir():
                # Create directory
                os.makedirs(extraction_path, exist_ok=True)
                # Set permissions if needed (but don't fail on this)
                try:
                    os.chmod(extraction_path, member.mode)
                except (OSError, IOError):
                    pass
                
            elif member.isfile():
                # Extract file content to temporary location, then move
                # Use os.open with O_NOFOLLOW equivalent via temp file approach
                parent_dir = os.path.dirname(extraction_path)
                os.makedirs(parent_dir, exist_ok=True)
                
                # Extract to temp file in same directory, then rename
                fd, temp_path = tempfile.mkstemp(dir=parent_dir)
                try:
                    with os.fdopen(fd, 'wb') as f:
                        fsrc = tar.extractfile(member)
                        if fsrc is not None:
                            shutil.copyfileobj(fsrc, f)
                            fsrc.close()
                    
                    # Set permissions before rename
                    os.chmod(temp_path, member.mode)
                    
                    # Atomic rename (doesn't follow symlinks in final component)
                    os.replace(temp_path, extraction_path)
                except:
                    try:
                        os.close(fd)
                    except:
                        pass
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
                    raise
                    
            elif member.issym():
                # Create symbolic link
                parent_dir = os.path.dirname(extraction_path)
                os.makedirs(parent_dir, exist_ok=True)
                
                # Remove existing file if present to avoid following symlinks
                try:
                    os.unlink(extraction_path)
                except (OSError, IOError):
                    pass
                
                # Use relative path for symlink target when possible
                # Compute relative path from extraction_path's parent to validated_link_target
                link_target = os.path.relpath(validated_link_target, parent_dir)
                os.symlink(link_target, extraction_path)
                
            elif member.islnk():
                # Hard link - check if target exists, defer if not
                if validated_link_target in validated_paths:
                    # Check if target already extracted
                    if os.path.exists(validated_link_target):
                        # Remove existing file at extraction path if present
                        try:
                            os.unlink(extraction_path)
                        except (OSError, IOError):
                            pass
                        os.link(validated_link_target, extraction_path)
                    else:
                        # Target not yet materialized, defer
                        deferred_hard_links.append((validated_link_target, extraction_path))
                else:
                    # Target not in validated paths, reject
                    tar.close()
                    return False
                    
        except (OSError, IOError, ValueError):
            tar.close()
            return False
    
    # Process deferred hard links
    for target_path, link_path in deferred_hard_links:
        try:
            if os.path.exists(target_path):
                # Remove existing file at link path if present
                try:
                    os.unlink(link_path)
                except (OSError, IOError):
                    pass
                os.link(target_path, link_path)
            else:
                # Target still doesn't exist, fail
                tar.close()
                return False
        except (OSError, IOError):
            tar.close()
            return False
    
    # Step 6: Close archive and return success
    tar.close()
    return True
