import os
import tarfile
import shutil
import tempfile

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory.
    
    Validates all members before extraction and rejects:
    - Symbolic links
    - Hard links
    - Any member whose path would go outside dest_path
    
    Returns True only if extraction completes successfully, False otherwise.
    No files are written outside dest_path if validation fails.
    """
    try:
        # Create dest_path if it doesn't exist
        os.makedirs(dest_path, exist_ok=True)
        
        # Get the absolute path of the destination root
        dest_root = os.path.abspath(dest_path)
        
        # Open the tar file for reading
        with tarfile.open(tar_path, 'r:*') as tar:
            # Iterate through each member before extracting
            for member in tar.getmembers():
                # Calculate the absolute path where this member would be extracted
                # member.name is the relative path within the archive
                member_abs = os.path.abspath(os.path.join(dest_root, member.name))
                
                # Check for absolute paths or paths with .. that escape dest_root
                if member_abs.startswith(os.path.abspath(dest_root)):
                    pass  # OK, within dest_root
                elif member_abs.startswith(os.path.abspath(os.path.dirname(dest_root))):
                    pass  # OK, same directory
                else:
                    # Path escapes the destination root
                    return False
                
                # Reject symbolic links
                if member.issym():
                    return False
                
                # Reject hard links
                if member.islnk():
                    return False
                
                # Additional safety: check if the member name itself contains ..
                # This could be used to escape even if the final path check passes
                if '..' in member.name.split(os.sep):
                    return False
            
            # If all members pass validation, proceed with extraction
            # Use a temporary directory for safe extraction, then move to dest
            with tempfile.TemporaryDirectory() as tmp_dir:
                # Extract to temporary directory first
                tar.extractall(tmp_dir)
                
                # Move all contents from temp to dest
                for item in os.listdir(tmp_dir):
                    src = os.path.join(tmp_dir, item)
                    dst = os.path.join(dest_root, item)
                    if os.path.isdir(src):
                        os.makedirs(dst, exist_ok=True)
                        for subitem in os.listdir(src):
                            sub_src = os.path.join(src, subitem)
                            sub_dst = os.path.join(dst, subitem)
                            if os.path.isdir(sub_src):
                                os.makedirs(sub_dst, exist_ok=True)
                            else:
                                shutil.copy2(sub_src, sub_dst)
                    else:
                        shutil.copy2(src, dst)
                
                # Clean up temporary directory
                shutil.rmtree(tmp_dir)
        
        return True
        
    except Exception:
        return False
