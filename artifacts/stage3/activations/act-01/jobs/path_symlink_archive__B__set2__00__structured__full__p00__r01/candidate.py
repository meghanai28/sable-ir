import os
import tarfile
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination path with strict path validation.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory for extraction.
        
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    try:
        # Resolve and normalize the destination path
        dest_path = os.path.realpath(dest_path)
        if not os.path.isdir(dest_path):
            return False
        
        # Open the tar file
        tar = tarfile.open(tar_path)
        
        try:
            # Extract members one by one to validate paths
            for member in tar.getmembers():
                # Normalize the member's target path
                member_path = os.path.normpath(member.name)
                
                # Resolve the full path of the member
                resolved_member_path = os.path.realpath(member_path)
                
                # Check if the resolved path is outside the destination
                if not resolved_member_path.startswith(dest_path + os.sep) and resolved_member_path != dest_path:
                    return False
                
                # Special check for symbolic links
                if member.issym() or member.islnk():
                    # Get the link target
                    link_target = member.linkname
                    resolved_link_target = os.path.realpath(link_target)
                    
                    # Check if the link target is outside the destination
                    if not resolved_link_target.startswith(dest_path + os.sep) and resolved_link_target != dest_path:
                        return False
                
                # Check for device files which can be dangerous
                if member.isdir() or member.isfile():
                    # Ensure the directory doesn't contain ..
                    if '..' in member_path.split(os.sep):
                        return False
        
            # If all validations pass, extract the archive
            tar.extractall(path=dest_path)
            
        finally:
            tar.close()
        
        return True
        
    except Exception:
        return False
