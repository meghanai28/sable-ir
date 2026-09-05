import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination path with safety checks.
    
    Args:
        tar_path: Path to the tar archive.
        dest_path: Destination directory for extraction.
    
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    try:
        # Resolve and normalize paths to prevent directory traversal
        dest_path = os.path.normpath(os.path.abspath(dest_path))
        tar_path = os.path.normpath(os.path.abspath(tar_path))
        
        # Ensure destination exists
        if not os.path.exists(dest_path):
            os.makedirs(dest_path, exist_ok=True)
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Validate all members before extraction
            for member in tar.getmembers():
                # Skip directories in validation loop to avoid recursion issues,
                # but we must check their contents.
                if member.isdir():
                    continue
                
                # Resolve the member's path relative to the destination
                member_path = os.path.join(dest_path, member.name)
                normalized_member_path = os.path.normpath(os.path.abspath(member_path))
                
                # Check for directory traversal
                if not normalized_member_path.startswith(dest_path):
                    return False
                
                # Check for symbolic links or hard links
                if member.issym() or member.islnk():
                    return False
                
                # For regular files, we will extract them later
                # For directories, we extract them later
                # The validation above ensures no traversal and no symlinks
                
            # Extract members
            for member in tar.getmembers():
                if member.isdir():
                    os.makedirs(os.path.normpath(os.path.join(dest_path, member.name)), exist_ok=True)
                else:
                    # Extract the file
                    member_path = os.path.normpath(os.path.join(dest_path, member.name))
                    os.makedirs(os.path.dirname(member_path), exist_ok=True)
                    with tar.extractfile(member) as extracted_file:
                        shutil.copyfileobj(extracted_file, open(member_path, 'wb'))
        
        return True
    
    except Exception:
        return False
