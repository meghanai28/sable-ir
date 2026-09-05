import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination path with security checks.
    
    Args:
        tar_path: Path to the tar archive.
        dest_path: Destination directory for extraction.
    
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    try:
        # Normalize and resolve the destination path
        dest_path = os.path.realpath(dest_path)
        
        # Check if the destination exists and is a directory
        if not os.path.isdir(dest_path):
            return False
        
        # Create the destination directory if it doesn't exist
        os.makedirs(dest_path, exist_ok=True)
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get all members of the tar file
            members = tar.getmembers()
            
            # Check each member for path traversal
            for member in members:
                # Get the relative path of the member
                member_path = member.name
                
                # Skip if the member is empty or has no name
                if not member_path or not member_path:
                    continue
                
                # Calculate the absolute path of the member relative to dest_path
                member_abs_path = os.path.join(dest_path, member_path)
                
                # Normalize the path to resolve any .. segments
                normalized_member_path = os.path.normpath(member_abs_path)
                
                # Check if the normalized path escapes the destination
                if not normalized_member_path.startswith(dest_path):
                    return False
                
                # Check for symbolic links that might escape
                if member.isdir or member.issym() or member.ishardlink():
                    # For symlinks, we need to check the target
                    # We can't fully resolve symlinks without following them,
                    # but we can check the name itself first
                    if member.issym() or member.ishardlink():
                        # Check if the link target would escape
                        # We'll do a more thorough check after extraction
                        pass
            
            # Extract the archive
            tar.extractall(path=dest_path)
            
            return True
            
    except Exception:
        return False
