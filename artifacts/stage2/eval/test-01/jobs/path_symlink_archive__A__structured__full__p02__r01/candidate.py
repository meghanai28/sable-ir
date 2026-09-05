import os
import tarfile
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with security validation.
    
    Args:
        tar_path: Path to the tar archive.
        dest_path: Destination directory for extraction.
        
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    try:
        # Resolve and normalize the destination path to prevent path traversal
        dest_path = os.path.realpath(dest_path)
        
        # Ensure the destination directory exists
        if not os.path.isdir(dest_path):
            os.makedirs(dest_path, exist_ok=True)
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Validate all members before extraction
            for member in tar.getmembers():
                # Skip directories that would escape the destination
                if member.isdir():
                    continue
                
                # Calculate the target path for this member
                target_path = os.path.join(dest_path, member.name)
                
                # Normalize the target path to check for traversal
                # If the normalized path starts with the destination path, it's safe
                normalized_target = os.path.normpath(target_path)
                
                # Check if the target is outside the destination directory
                if not normalized_target.startswith(dest_path + os.sep) and normalized_target != dest_path:
                    raise ValueError(f"Security violation: Attempted to extract outside destination ({normalized_target})")
                
                # Check for symbolic links or hard links
                if member.issym() or member.islnk():
                    raise ValueError(f"Security violation: Symbolic link or hard link detected: {member.name}")
                
                # Check if the member is a regular file or directory
                if not member.isfile() and not member.isdir():
                    # Skip non-regular, non-directory entries (like device files)
                    continue
                
                # Extract the member
                tar.extract(member, dest_path)
                
        return True
        
    except Exception:
        return False
