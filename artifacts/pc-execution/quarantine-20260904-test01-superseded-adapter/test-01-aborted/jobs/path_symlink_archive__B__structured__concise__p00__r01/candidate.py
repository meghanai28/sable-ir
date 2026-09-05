import os
import tarfile
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory with strict path validation.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory where the archive will be extracted.
        
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    try:
        # Normalize dest_path to absolute form and resolve any . or .. segments
        dest_path = os.path.normpath(os.path.abspath(dest_path))
        
        # Guard: Reject absolute paths that start with root or other absolute prefixes
        if dest_path.startswith(os.sep) or dest_path.startswith('\\'):
            return False
            
        # Create the destination directory if it doesn't exist
        os.makedirs(dest_path, exist_ok=True)
        
        with tarfile.open(tar_path, 'r:*') as tar:
            # Walk through each member of the archive
            for member in tar.getmembers():
                # Resolve the full path for the member
                member_path = os.path.join(dest_path, member.name)
                
                # Normalize the member path to handle . and ..
                member_path = os.path.normpath(member_path)
                
                # Guard: Ensure the member path does not escape the dest_path
                if not member_path.startswith(dest_path):
                    return False
                
                # Guard: Check for absolute paths in member names
                if os.path.isabs(member.name):
                    return False
                
                # Validate link targets before extraction
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    resolved_link = os.path.normpath(os.path.join(dest_path, link_target))
                    if not resolved_link.startswith(dest_path):
                        return False
                    # Guard: Ensure link target is not an absolute path
                    if os.path.isabs(link_target):
                        return False
                
                # Guard: Check hard links
                if member.islnk():
                    link_target = member.linkname
                    resolved_link = os.path.normpath(os.path.join(dest_path, link_target))
                    if not resolved_link.startswith(dest_path):
                        return False
                
                # Extract the member
                try:
                    tar.extract(member, dest_path)
                except Exception:
                    return False
                    
        return True
        
    except Exception:
        return False
