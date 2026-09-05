import os
import tarfile
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory with security checks.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory path.
    
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    # Validate inputs
    if not tar_path or not dest_path:
        return False
    
    # Ensure dest_path exists and is a directory
    try:
        if not os.path.exists(dest_path):
            os.makedirs(dest_path, exist_ok=True)
        if not os.path.isdir(dest_path):
            return False
    except (OSError, PermissionError):
        return False
    
    # Resolve the absolute path of the destination
    try:
        resolved_dest = os.path.realpath(dest_path)
    except (OSError, ValueError):
        return False
    
    # Open the tar file for reading
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Validate all members before extraction
            for member in tar.getmembers():
                # Get the target path for this member
                target = os.path.join(resolved_dest, member.name)
                
                # Normalize the target to prevent directory traversal
                normalized_target = os.path.normpath(target)
                
                # Resolve the target to check for escape attempts
                resolved_target = os.path.realpath(normalized_target)
                
                # Check if the resolved target is within the destination directory
                if not resolved_target.startswith(resolved_dest + os.sep) and resolved_target != resolved_dest:
                    return False
                
                # Reject symbolic links and hard links that could be malicious
                if member.issym() or member.islnk():
                    return False
                
                # Reject devices, fifos, etc. if they are not regular files or directories
                if not (member.isfile() or member.isdir()):
                    return False
            
            # If all validations pass, extract the archive
            tar.extractall(path=resolved_dest)
            return True
            
    except (tarfile.TarError, OSError, PermissionError):
        return False
