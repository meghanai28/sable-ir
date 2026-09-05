import os
import tarfile
import shutil
import tempfile

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination path with strict security controls.
    
    Args:
        tar_path: Path to the tar archive.
        dest_path: Destination directory for extraction.
        
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    try:
        # Normalize the destination path to remove any trailing slashes
        dest_path = os.path.normpath(dest_path)
        
        # Reject absolute paths
        if os.path.isabs(dest_path):
            return False
        
        # Create a temporary directory for extraction
        with tempfile.TemporaryDirectory() as temp_extract_dir:
            # Extract the archive to the temporary directory
            with tarfile.open(tar_path, 'r:*') as tar:
                tar.extractall(path=temp_extract_dir)
            
            # List all files in the temporary directory
            files_to_extract = []
            for root, dirs, files in os.walk(temp_extract_dir):
                for file in files:
                    full_path = os.path.join(root, file)
                    files_to_extract.append(full_path)
            
            # Validate each file to ensure it doesn't escape the destination
            for file_path in files_to_extract:
                # Calculate the relative path from the temp directory
                rel_path = os.path.relpath(file_path, temp_extract_dir)
                
                # Ensure the relative path doesn't contain '..'
                if '..' in rel_path.split(os.sep):
                    return False
                
                # Calculate the final destination path
                final_dest = os.path.normpath(os.path.join(dest_path, rel_path))
                
                # Ensure the final destination is within the dest_path
                if not final_dest.startswith(dest_path + os.sep) and final_dest != dest_path:
                    return False
            
            # If validation passes, extract the files to the destination
            for file_path in files_to_extract:
                rel_path = os.path.relpath(file_path, temp_extract_dir)
                final_dest = os.path.normpath(os.path.join(dest_path, rel_path))
                shutil.copy2(file_path, final_dest)
            
            return True
            
    except Exception:
        return False
