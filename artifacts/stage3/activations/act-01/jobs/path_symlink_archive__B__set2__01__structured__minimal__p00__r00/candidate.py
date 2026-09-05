import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory for extraction.
        
    Returns:
        True if extraction completes successfully, False otherwise.
        
    Raises:
        ValueError: If the destination path or any archive member would escape the intended destination.
    """
    # Normalize and resolve the destination path to prevent directory traversal
    dest_path = os.path.normpath(dest_path)
    if dest_path.startswith(os.path.curdir) or dest_path.startswith(os.path.pardir):
        raise ValueError("dest_path contains .. segments")
    
    # Ensure the destination directory exists
    if not os.path.exists(dest_path):
        os.makedirs(dest_path)
    
    # Resolve the tar file path
    tar_file = os.path.normpath(tar_path)
    
    # Validate that the tar file exists
    if not os.path.isfile(tar_file):
        return False
    
    try:
        with tarfile.open(tar_file, 'r:*') as tar:
            # Get the list of members to validate before extraction
            members = tar.getnames()
            
            for member in members:
                # Resolve the member's destination relative to dest_path
                member_dest = os.path.normpath(os.path.join(dest_path, member))
                
                # Check for directory traversal
                if not member_dest.startswith(dest_path) or member_dest == dest_path:
                    raise ValueError(f"Archive member '{member}' would escape the destination directory")
                
                # Ensure no parent directory traversal in the resolved path
                if '..' in member or member.startswith('/'):
                    raise ValueError(f"Archive member '{member}' contains unsafe characters")
            
            # Extract the archive
            tar.extractall(dest_path)
            
            return True
            
    except Exception:
        return False
