import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory with security validation.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory where the archive will be extracted.
    
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    # Validate inputs exist and are accessible
    if not os.path.isfile(tar_path):
        return False
    
    # Create dest_path if it doesn't exist
    try:
        os.makedirs(dest_path, exist_ok=True)
    except Exception:
        return False
    
    # Resolve the absolute path of the destination
    resolved_dest = os.path.abspath(dest_path)
    
    # Open the tar file for reading
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Validate all members before extracting any
            for member in tar.getmembers():
                # Get the absolute path of the member's target relative to dest_path
                target_dir = os.path.join(resolved_dest, member.name)
                resolved_target = os.path.abspath(target_dir)
                
                # Security check: ensure the resolved target is within dest_path
                # This prevents directory traversal attacks
                if not (resolved_target.startswith(resolved_dest + os.sep) or resolved_target == resolved_dest):
                    return False
                
                # Reject symbolic links and hard links
                if member.issym() or member.islnk():
                    return False
            
            # If all validations pass, perform the extraction
            tar.extractall(path=resolved_dest)
            return True
            
    except Exception:
        return False
