import os
import tarfile
import tempfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict path validation.
    
    Args:
        tar_path: Path to the tar archive (untrusted).
        dest_path: Destination directory for extraction (untrusted).
        
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    try:
        # Resolve and normalize the destination path
        resolved_dest = os.path.realpath(dest_path)
        
        # Ensure dest_path is a directory
        if not os.path.isdir(resolved_dest):
            return False
        
        # Create a temporary directory for safe extraction
        with tempfile.TemporaryDirectory() as temp_dir:
            # Extract the archive to the temporary directory
            with tarfile.open(tar_path, 'r:*') as tar:
                # Validate and extract members to temp directory
                for member in tar.getmembers():
                    # Construct the target path in the temp directory
                    target_in_temp = os.path.join(temp_dir, member.name)
                    
                    # Normalize the target path
                    normalized_target = os.path.realpath(target_in_temp)
                    
                    # Check if the normalized target is within the temp directory
                    if not normalized_target.startswith(temp_dir + os.sep) and normalized_target != temp_dir:
                        # This check handles the case where normalized_target is the temp_dir itself
                        # but the member name is empty or starts with ..
                        return False
                    
                    # Extract the member to the temp directory
                    tar.extract(member, temp_dir)
                
                # Now move the extracted contents to the final destination
                # We need to handle the case where dest_path might be a file or directory
                # First, remove any existing files in dest_path to avoid conflicts
                for root, dirs, files in os.walk(resolved_dest):
                    for name in files:
                        os.remove(os.path.join(root, name))
                    # Remove directories that are not the final dest_path
                    if root != resolved_dest:
                        shutil.rmtree(root)
                
                # Copy the contents from temp_dir to resolved_dest
                for root, dirs, files in os.walk(temp_dir):
                    for name in files:
                        src = os.path.join(root, name)
                        dst = os.path.join(resolved_dest, src[len(temp_dir):] + os.sep if src != temp_dir else src)
                        # Handle the case where src is just the temp_dir itself
                        if src == temp_dir:
                            dst = resolved_dest
                        else:
                            dst = os.path.join(resolved_dest, src[len(temp_dir):])
                        
                        if os.path.exists(dst):
                            os.remove(dst)
                        if os.path.isdir(src):
                            os.makedirs(dst, exist_ok=True)
                            shutil.copytree(src, dst)
                        else:
                            shutil.copy2(src, dst)
                
                # Verify that all files are within dest_path
                for root, dirs, files in os.walk(resolved_dest):
                    for name in files:
                        file_path = os.path.join(root, name)
                        if not file_path.startswith(resolved_dest + os.sep) and file_path != resolved_dest:
                            return False
                    
                    # Check for directories
                    if root != resolved_dest:
                        shutil.rmtree(root)
                
                return True
                
    except Exception:
        return False
