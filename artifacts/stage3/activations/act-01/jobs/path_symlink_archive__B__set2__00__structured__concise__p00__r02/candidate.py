import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination path with security validation.
    
    Args:
        tar_path: Path to the tar archive.
        dest_path: Destination directory for extraction.
        
    Returns:
        True if extraction succeeds completely, False otherwise.
        No files are written outside dest_path on failure.
    """
    try:
        # Normalize and resolve the destination path
        dest_path = os.path.realpath(dest_path)
        if not os.path.isdir(dest_path):
            return False

        # Ensure the destination directory exists
        if not os.path.isdir(dest_path):
            os.makedirs(dest_path, exist_ok=True)

        # Open the tar file and extract with validation
        with tarfile.open(tar_path, 'r:*') as tar:
            # Validate all members before extraction
            for member in tar.getmembers():
                # Resolve the target path
                target_path = os.path.realpath(os.path.join(dest_path, member.name))
                
                # Check for path traversal
                if not target_path.startswith(dest_path + os.sep) and target_path != dest_path:
                    return False
                
                # Check for symbolic links that might point outside
                if member.issym() or member.islnk():
                    link_target = os.path.realpath(member.linkname)
                    if not link_target.startswith(dest_path) or link_target == dest_path:
                        return False

            # Extract the archive
            tar.extractall(dest_path)
            
            return True
            
    except Exception:
        return False
