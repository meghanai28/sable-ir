import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory where the archive will be extracted.
        
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    try:
        # Ensure the destination directory exists
        os.makedirs(dest_path, exist_ok=True)
        
        # Create a temporary directory for safe extraction
        temp_dir = os.path.join(os.path.dirname(os.path.abspath(dest_path)), '.temp_extract_')
        os.makedirs(temp_dir, exist_ok=True)
        
        try:
            with tarfile.open(tar_path, 'r:*') as tar:
                # Get all members and validate them
                members = tar.getmembers()
                
                for member in members:
                    # Check for symbolic links
                    if member.issym():
                        return False
                    
                    # Check for hard links
                    if member.islnk():
                        return False
                    
                    # Resolve the target path relative to dest_path
                    # If the member is a directory, we need to check if it contains ..
                    # If it's a file, we need to check if the path contains ..
                    
                    # Get the relative path from dest_path
                    relative_path = os.path.relpath(member.name, dest_path)
                    
                    # Check for path traversal
                    if '..' in relative_path or relative_path.startswith('..'):
                        return False
                    
                    # For directories, ensure the directory path doesn't contain ..
                    # For files, ensure the file path doesn't contain ..
                    
                    # Additional check: if the member is a directory, we need to make sure
                    # that creating the directory doesn't go outside dest_path
                    if member.isdir():
                        # Check if the directory path contains ..
                        if '..' in relative_path or relative_path.startswith('..'):
                            return False
                    
                    # Extract the member to the temporary directory
                    member.archive(temp_dir)
                    
                # Now extract all members to the destination directory
                for member in members:
                    if member.isdir():
                        os.makedirs(os.path.join(dest_path, member.name), exist_ok=True)
                    else:
                        # Extract the file
                        with tarfile.open(tar_path, 'r:*') as tar:
                            tar.extract(member, dest_path)
                            
        except Exception:
            return False
        finally:
            # Clean up temporary directory
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
        
        return True
        
    except Exception:
        return False
