import os
import tarfile
import shutil
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory with security validations.
    
    Args:
        tar_path: Path to the tar archive.
        dest_path: Destination directory for extraction.
    
    Returns:
        True if extraction succeeds completely, False otherwise.
    """
    try:
        # Resolve and normalize paths to prevent directory traversal
        tar_dir = os.path.dirname(os.path.abspath(tar_path))
        dest_dir = os.path.abspath(dest_path)
        
        # Ensure dest_dir exists
        os.makedirs(dest_dir, exist_ok=True)
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get all members before any extraction
            members = tar.getmembers()
            
            # Validate all members before extraction
            for member in members:
                # Skip directories if we only want files, but the spec says "regular file or directory"
                # Check for symbolic links or hard links
                if member.issym() or member.islnk():
                    raise ValueError(f"Symbolic link or hard link detected: {member.name}")
                
                # Check for absolute paths or path traversal
                if member.name.startswith('/') or '..' in member.name:
                    raise ValueError(f"Path traversal detected in member: {member.name}")
                
                # Construct the target path
                target_path = os.path.join(dest_dir, member.name)
                
                # Normalize the target path to check for escapes
                normalized_target = os.path.normpath(target_path)
                
                # Ensure the normalized target is within the destination directory
                if not normalized_target.startswith(dest_dir + os.sep) and normalized_target != dest_dir:
                    raise ValueError(f"Extraction would escape destination: {member.name}")
            
            # Extract all members
            tar.extractall(path=dest_dir)
            
            return True
            
    except Exception as e:
        return False
