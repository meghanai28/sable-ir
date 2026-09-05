import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to the specified destination directory.
    
    This function validates the tar archive before extraction to ensure
    security against path traversal and symbolic link attacks.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory where the archive should be extracted.
        
    Returns:
        True if extraction is complete and successful, False otherwise.
    """
    # Validate input paths
    if not os.path.isfile(tar_path):
        return False
    
    # Create the destination directory if it doesn't exist
    try:
        os.makedirs(dest_path, exist_ok=True)
    except OSError:
        return False
    
    # Normalize the destination path to remove any trailing slashes or relative components
    dest_path = os.path.normpath(dest_path)
    
    # Open the tar file and iterate through members
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            for member in tar.getmembers():
                # Check if the member is a symbolic link or hard link
                if member.issym() or member.islnk():
                    return False
                
                # Calculate the absolute path of the member's destination
                # We need to check this relative to the dest_path
                dest_member_path = os.path.normpath(os.path.join(dest_path, member.name))
                
                # Check for path traversal attempts
                # Ensure the resolved path is within the dest_path directory
                if not dest_member_path.startswith(dest_path + os.sep) and dest_member_path != dest_path:
                    return False
                
                # Check if the member is a directory
                if member.isdir():
                    # Create the directory if it doesn't exist
                    try:
                        os.makedirs(dest_member_path, exist_ok=True)
                    except OSError:
                        return False
                else:
                    # Check if the parent directory exists
                    parent_dir = os.path.dirname(dest_member_path)
                    if not os.path.exists(parent_dir):
                        try:
                            os.makedirs(parent_dir, exist_ok=True)
                        except OSError:
                            return False
                    
                    # Extract the file
                    try:
                        tar.extract(member, dest_path)
                    except (tarfile.TarError, OSError):
                        return False
    
    except (tarfile.TarError, OSError):
        return False
    
    return True
