import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination path with security validation.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory path for extraction.
    
    Returns:
        True if extraction completes successfully with all members inside dest_path.
        False if validation fails or extraction is interrupted.
    """
    try:
        # Resolve and normalize paths to handle symlinks and .. segments
        resolved_tar = os.path.realpath(tar_path)
        resolved_dest = os.path.realpath(dest_path)
        
        # Validate that tar_path exists
        if not os.path.exists(resolved_tar):
            return False
        
        # Create destination directory if it doesn't exist
        os.makedirs(resolved_dest, exist_ok=True)
        
        # Extract the tar file
        with tarfile.open(resolved_tar, 'r:*') as tar:
            # Validate all members before extraction
            for member in tar.getmembers():
                # Get the resolved path for this member
                member_path = os.path.join(resolved_dest, member.name)
                
                # Resolve the path to check for .. escapes
                resolved_member_path = os.path.realpath(member_path)
                
                # Ensure the resolved member path is within the resolved destination
                if not resolved_member_path.startswith(resolved_dest + os.sep) and resolved_member_path != resolved_dest:
                    return False
                
                # Additional check for absolute paths in member names
                if os.path.isabs(member.name):
                    return False
            
            # Perform the extraction with safe settings
            tar.extractall(path=resolved_dest)
        
        return True
        
    except Exception:
        return False
