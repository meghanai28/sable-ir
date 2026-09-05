import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to the specified destination directory.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory where the archive should be extracted.
    
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    # Normalize the destination path to an absolute path without trailing slashes
    dest_path = os.path.normpath(dest_path)
    
    # Ensure the destination directory exists
    if not os.path.isdir(dest_path):
        return False
    
    # Define the absolute path for the destination root
    dest_root = os.path.abspath(dest_path)
    
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Extract members one by one to validate each path before extraction
            for member in tar.getmembers():
                # Skip symbolic links and hard links as per ORDER constraint
                if member.issym() or member.islnk():
                    return False
                
                # Resolve the target path for the member
                # If the member has no path (e.g., root of archive), it goes to dest_root
                # Otherwise, prepend the dest_root to the member's name
                if member.name == '':
                    member_path = dest_root
                else:
                    member_path = os.path.join(dest_root, member.name)
                
                # Normalize the member path to handle .. and .
                member_path = os.path.normpath(member_path)
                
                # Check if the resolved path escapes the destination root
                # We need to ensure the path is within dest_root
                if not member_path.startswith(dest_root + os.sep) and member_path != dest_root:
                    return False
                
                # Extract the member
                tar.extract(member, dest_path)
    
    except (tarfile.TarError, OSError, IOError):
        return False
    
    return True
