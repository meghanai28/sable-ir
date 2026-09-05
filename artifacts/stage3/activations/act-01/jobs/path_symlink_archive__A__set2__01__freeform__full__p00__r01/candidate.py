import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory with strict path validation.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory where the archive should be extracted.
    
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    try:
        # Resolve and normalize the destination path
        dest_path = os.path.realpath(dest_path)
        
        # Validate that dest_path is not absolute or escapes root
        if not dest_path.startswith(os.sep) and dest_path != os.path.sep:
            dest_path = os.path.join(os.path.dirname(os.path.realpath('.')), dest_path)
        
        # Ensure the destination directory exists
        os.makedirs(dest_path, exist_ok=True)
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Extract each member with validation
            for member in tar.getmembers():
                # Check for absolute paths or .. components
                if member.name.startswith('/') or '..' in member.name:
                    raise ValueError(f"Archive contains dangerous path: {member.name}")
                
                # Resolve the member's path relative to dest_path
                resolved_member_path = os.path.join(dest_path, member.name)
                resolved_member_path = os.path.realpath(resolved_member_path)
                
                # Ensure the resolved path is within dest_path
                if not resolved_member_path.startswith(dest_path + os.sep) and resolved_member_path != dest_path:
                    raise ValueError(f"Archive member escapes destination: {member.name}")
                
                # Skip directory members that are not needed (only extract files)
                if member.isdir():
                    continue
                
                # Extract the member
                tar.extract(member, dest_path)
                
    except Exception as e:
        return False
    
    return True
