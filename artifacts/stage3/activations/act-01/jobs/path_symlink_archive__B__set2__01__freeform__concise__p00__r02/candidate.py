import os
import tarfile
import tempfile

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict path validation to prevent escape attacks.
    
    Args:
        tar_path: Path to the tar archive.
        dest_path: Destination directory for extraction.
    
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    try:
        # Resolve the root directory based on dest_path
        # We treat dest_path as the root. If it's absolute, use it directly.
        # If relative, resolve it relative to the current working directory, but ensure
        # we don't accidentally use a different cwd.
        resolved_root = os.path.abspath(dest_path)
        
        # Normalize the root to remove any trailing slashes or .. components
        resolved_root = os.path.normpath(resolved_root)
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get all members
            members = tar.getnames()
            
            for member in members:
                # Resolve the member's path relative to the destination root
                # We need to resolve the path to check for .. escapes
                # The member name might contain .., so we resolve it
                member_path = os.path.normpath(os.path.join(resolved_root, member))
                
                # Check if the resolved path escapes the root
                if not member_path.startswith(resolved_root + os.sep) and member_path != resolved_root:
                    # This handles cases where the path is exactly the root or starts with it
                    # We also need to handle the case where the path is a subdirectory
                    # The safest check is to ensure the resolved path is within the root
                    if not member_path.startswith(resolved_root):
                        raise ValueError(f"Member path {member} escapes destination root {resolved_root}")
                
                # Additional check: ensure no .. in the resolved path that goes above root
                # We can do this by checking if the resolved path starts with the root + separator
                # or is exactly the root
                if member_path == resolved_root:
                    # This is valid (root itself)
                    pass
                elif not member_path.startswith(resolved_root + os.sep):
                    raise ValueError(f"Member path {member} escapes destination root {resolved_root}")
                
                # Create the directory structure if needed
                member_dir = os.path.dirname(member_path)
                if member_dir:
                    os.makedirs(member_dir, exist_ok=True)
            
            # Now extract the archive
            tar.extractall(path=resolved_root)
            
            return True
            
    except Exception as e:
        return False
