import os
import tarfile
import shutil
import tempfile

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict path validation to prevent
    directory traversal escapes. Returns True on complete success, False otherwise.
    """
    # Normalize dest_path to an absolute path
    try:
        dest_path = os.path.realpath(dest_path)
    except (ValueError, OSError):
        return False

    # Ensure dest_path is under the root directory
    if not dest_path.startswith(os.sep) and dest_path != os.sep:
        return False

    # Create a temporary directory for safe extraction
    safe_extract_dir = None
    try:
        safe_extract_dir = tempfile.mkdtemp()
    except (ValueError, OSError):
        return False

    try:
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Validate each member before extraction
            for member in tar.getmembers():
                # Resolve the member's path relative to the archive root
                member_dir = os.path.dirname(member.name)
                member_file = os.path.basename(member.name)
                
                # Construct the full path relative to dest_path
                relative_path = os.path.join(member_dir, member_file)
                
                # Resolve the full path
                full_path = os.path.normpath(os.path.join(dest_path, relative_path))
                
                # Check for directory traversal
                if not full_path.startswith(dest_path + os.sep) and full_path != dest_path:
                    return False
                
                # Also check if the directory part escapes
                if member_dir and not os.path.normpath(os.path.join(dest_path, member_dir)).startswith(dest_path + os.sep):
                    return False
            
            # Extract to the safe temporary directory first
            tar.extractall(safe_extract_dir)
            
            # Move the extracted contents to the destination
            if os.path.exists(safe_extract_dir):
                shutil.rmtree(safe_extract_dir)
            
            # Create the destination directory structure if needed
            if not os.path.exists(dest_path):
                os.makedirs(dest_path)
            
            # Move files from safe_extract_dir to dest_path
            for root, dirs, files in os.walk(safe_extract_dir):
                # Calculate relative path from safe_extract_dir
                rel_root = os.path.relpath(root, safe_extract_dir)
                
                # Create destination directory
                dest_root = os.path.join(dest_path, rel_root)
                os.makedirs(dest_root, exist_ok=True)
                
                # Move files
                for file in files:
                    src_file = os.path.join(root, file)
                    dst_file = os.path.join(dest_root, file)
                    shutil.move(src_file, dst_file)
            
            # Clean up
            shutil.rmtree(safe_extract_dir)
            
            return True
            
    except (tarfile.TarError, ValueError, OSError, PermissionError):
        return False
    finally:
        # Ensure cleanup of temporary directory
        if safe_extract_dir and os.path.exists(safe_extract_dir):
            try:
                shutil.rmtree(safe_extract_dir)
            except:
                pass
