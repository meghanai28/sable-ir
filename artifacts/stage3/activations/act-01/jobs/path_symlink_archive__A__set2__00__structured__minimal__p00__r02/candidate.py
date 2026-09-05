import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory, ensuring no path traversal.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory where the archive should be extracted.
        
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    # Normalize the destination path to remove any trailing slashes and resolve to an absolute path
    dest_path = os.path.normpath(dest_path)
    
    # Ensure dest_path is absolute
    if not os.path.isabs(dest_path):
        dest_path = os.path.abspath(dest_path)
    
    # Verify the destination directory exists
    if not os.path.isdir(dest_path):
        return False
    
    # Open the tar file
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Extract members one by one to validate each path
            for member in tar.getmembers():
                # Construct the full destination path for this member
                # We use normpath to handle any . or .. in the member name
                member_dest = os.path.normpath(os.path.join(dest_path, member.name))
                
                # Check if the destination path escapes the root
                if not member_dest.startswith(dest_path + os.sep) and member_dest != dest_path:
                    return False
                
                # Check if the parent directory exists, create if needed
                parent_dir = os.path.dirname(member_dest)
                if not os.path.exists(parent_dir):
                    os.makedirs(parent_dir)
                
                # Extract the member
                tar.extract(member, dest_path)
                
    except (tarfile.TarError, OSError):
        return False
    
    return True
