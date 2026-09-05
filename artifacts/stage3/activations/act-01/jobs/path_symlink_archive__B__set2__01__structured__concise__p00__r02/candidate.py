import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory safely.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory where the archive should be extracted.
    
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    # Normalize the destination path to an absolute path without trailing slashes
    dest_path = os.path.normpath(os.path.abspath(dest_path))
    
    # Ensure the destination directory exists, create if it doesn't
    try:
        os.makedirs(dest_path, exist_ok=True)
    except OSError:
        return False
    
    # Validate tar_path exists and is a file
    if not os.path.isfile(tar_path):
        return False
    
    # Resolve the directory of the tar file to prevent directory traversal via tar contents
    tar_dir = os.path.dirname(os.path.abspath(tar_path))
    
    # Validate that the tar file itself is not in a parent directory of dest_path
    if tar_dir == os.path.dirname(dest_path) or tar_dir == dest_path:
        pass  # This is acceptable
    elif os.path.commonpath([tar_dir, dest_path]) != tar_dir:
        return False
    
    # Create a temporary directory to extract to, then move to dest_path
    # This ensures we never write outside the intended destination
    temp_dir = None
    try:
        temp_dir = os.path.join(dest_path, '.temp_extract')
        os.makedirs(temp_dir, exist_ok=True)
        
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get all member names
            members = tar.getnames()
            
            # Validate each member name to prevent directory traversal within the archive
            for member in members:
                # Resolve the member's target path relative to the temp extraction directory
                member_path = os.path.join(temp_dir, member)
                
                # Normalize the path to resolve any .. or .
                normalized_member_path = os.path.normpath(member_path)
                
                # Ensure the normalized path is still within the temp directory
                if not normalized_member_path.startswith(temp_dir + os.sep) and normalized_member_path != temp_dir:
                    return False
            
            # Extract to the temporary directory
            tar.extractall(temp_dir)
            
            # Move all extracted files to the destination
            for root, dirs, files in os.walk(temp_dir):
                # Skip the temp directory itself
                if root == temp_dir:
                    continue
                    
                for dir in dirs:
                    src_dir = os.path.join(root, dir)
                    dst_dir = os.path.join(dest_path, dir)
                    if not os.path.exists(dst_dir):
                        os.makedirs(dst_dir)
                
                for file in files:
                    src_file = os.path.join(root, file)
                    dst_file = os.path.join(dest_path, file)
                    if not os.path.exists(dst_file):
                        shutil.copy2(src_file, dst_file)
            
            # Clean up the temporary directory
            shutil.rmtree(temp_dir, ignore_errors=True)
            
        return True
        
    except (tarfile.TarError, OSError):
        return False
    finally:
        # Ensure cleanup of temp directory if it was created
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
