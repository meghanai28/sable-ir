import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination path, ensuring no path traversal vulnerabilities.
    
    Args:
        tar_path (str): Path to the tar archive.
        dest_path (str): Destination directory for extraction.
    
    Returns:
        bool: True if extraction completes successfully, False otherwise.
    """
    # Normalize and resolve the destination path to prevent directory traversal
    dest_path = os.path.normpath(dest_path)
    dest_dir = os.path.realpath(dest_path)
    
    # Check if destination exists, create if necessary
    if not os.path.isdir(dest_dir):
        try:
            os.makedirs(dest_dir)
        except OSError:
            return False
    
    # Validate tar_path exists
    if not os.path.isfile(tar_path):
        return False
    
    # Open the tar file and iterate over members
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            for member in tar.getmembers():
                # Resolve the member's path relative to the destination
                member_path = os.path.join(dest_dir, member.name)
                member_real_path = os.path.realpath(member_path)
                
                # Check for path traversal
                if not member_real_path.startswith(dest_dir):
                    return False
                
                # Ensure the directory exists for the member's location
                member_dir = os.path.dirname(member_path)
                if not os.path.exists(member_dir):
                    os.makedirs(member_dir)
                
                # Extract the member
                tar.extract(member, dest_dir)
    except (tarfile.TarError, OSError):
        return False
    
    return True
