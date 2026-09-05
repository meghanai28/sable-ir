import os
import tarfile
import shutil

def _normalize_path(path: str) -> str:
    """Normalize a path to remove redundant separators and resolve .. safely."""
    return os.path.normpath(path)

def _is_safe_relative_path(target_path: str, dest_root: str) -> bool:
    """Check if target_path is safely within dest_root."""
    # Normalize both paths
    norm_target = _normalize_path(target_path)
    norm_dest = _normalize_path(dest_root)
    
    # Ensure target starts with dest_root
    if not norm_target.startswith(norm_dest + os.sep):
        return False
    
    # Additional check to prevent edge cases with trailing slashes
    if norm_target == norm_dest:
        return False
        
    return True

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path.
    
    Args:
        tar_path: Path to the tar archive.
        dest_path: Destination directory for extraction.
        
    Returns:
        True if extraction completes successfully, False otherwise.
        No files are written outside dest_path on failure.
    """
    # Normalize destination path immediately
    dest_path = _normalize_path(dest_path)
    
    # Create destination directory if it doesn't exist
    try:
        os.makedirs(dest_path, exist_ok=True)
    except Exception:
        return False
    
    # Read the archive members without extracting
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            members = tar.getnames()
            
            # Validate all members before extraction
            for member_name in members:
                # Resolve the member's potential destination
                # We need to construct the full path considering the member's name
                # For a member named "foo/bar", the destination would be dest_path + "foo/bar"
                # But we must be careful with member names that might start with ..
                
                # Construct the relative path from dest_path
                if member_name.startswith('..'):
                    return False
                
                # Get the full path if it's a directory or file
                # We need to check if the member name itself or its components escape
                # The safest approach is to resolve the full path and check
                full_path = dest_path + os.sep + member_name
                
                # Normalize the full path
                norm_full_path = _normalize_path(full_path)
                
                # Check if it escapes dest_path
                if not _is_safe_relative_path(norm_full_path, dest_path):
                    return False
                
                # Check for symbolic links
                if member_name.endswith('/'):
                    # It's a directory
                    continue
                else:
                    # It's a file
                    continue
            
            # Also check for symlinks in the archive metadata
            # We need to check the linkname field for each member
            for member in tar.getmembers():
                if member.isfile() or member.isdir():
                    # Check if the member name escapes
                    if not _is_safe_relative_path(member.name, dest_path):
                        return False
                elif member.issym() or member.islnk():
                    # Check if the link target escapes
                    link_target = member.linkname
                    if not _is_safe_relative_path(link_target, dest_path):
                        return False
                    # Also check if the link target points outside dest_path
                    # The link target should be relative to the file being linked
                    # We need to resolve the link target relative to the file's location
                    if member.isfile() or member.isdir():
                        file_path = dest_path + os.sep + member.name
                        norm_file_path = _normalize_path(file_path)
                        # Check if the link target is within the file's directory or dest_path
                        if not _is_safe_relative_path(link_target, norm_file_path):
                            return False
                        # Ensure the link target doesn't escape dest_path
                        if not _is_safe_relative_path(link_target, dest_path):
                            return False
            else:
                # All members passed validation, proceed with extraction
                with tarfile.open(tar_path, 'r:*') as tar:
                    for member in tar:
                        if member.isfile():
                            member_path = os.path.join(dest_path, member.name)
                            os.makedirs(os.path.dirname(member_path), exist_ok=True)
                            tar.extract(member, dest_path)
                        elif member.isdir():
                            dir_path = os.path.join(dest_path, member.name)
                            os.makedirs(dir_path, exist_ok=True)
                        elif member.issym():
                            member_path = os.path.join(dest_path, member.name)
                            os.makedirs(os.path.dirname(member_path), exist_ok=True)
                            tar.extractmember(member)
                        elif member.islnk():
                            member_path = os.path.join(dest_path, member.name)
                            os.makedirs(os.path.dirname(member_path), exist_ok=True)
                            tar.extractmember(member)
                
                return True
    except Exception:
        return False
