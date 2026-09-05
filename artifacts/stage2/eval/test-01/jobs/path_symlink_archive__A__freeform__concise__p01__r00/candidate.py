import os
import tarfile
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict path validation to prevent
    directory traversal attacks. Returns True on complete success, False otherwise.
    """
    try:
        # Resolve and normalize the destination path
        dest_path = os.path.realpath(dest_path)
        
        # Ensure dest_path exists and is a directory
        if not os.path.isdir(dest_path):
            return False
        
        # Create the destination directory if it doesn't exist
        os.makedirs(dest_path, exist_ok=True)
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get the absolute path of the tar file for reference
            tar_dir = os.path.dirname(os.path.realpath(tar_path))
            
            for member in tar.getmembers():
                # Skip symbolic links and hard links entirely
                if member.issym() or member.islnk():
                    return False
                
                # Calculate the target path
                target_path = os.path.join(dest_path, member.name)
                
                # Normalize the target path to resolve .. and .
                normalized_target = os.path.normpath(target_path)
                
                # Check if the normalized target escapes the destination directory
                if not normalized_target.startswith(dest_path + os.sep) and normalized_target != dest_path:
                    return False
                
                # Additional check to ensure the resolved path is within dest_path
                # This handles cases where normpath might resolve to something unexpected
                resolved_target = os.path.realpath(normalized_target)
                
                if not resolved_target.startswith(dest_path):
                    return False
                
                # Extract the member
                tar.extract(member, dest_path)
            
            return True
            
    except Exception:
        return False
