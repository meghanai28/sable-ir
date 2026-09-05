import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory with strict security validation.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory where the archive will be extracted.
        
    Returns:
        True if extraction completes successfully, False otherwise.
        
    Raises:
        ValueError: If the archive contains symbolic links, hard links, or targets outside dest_path.
        FileNotFoundError: If the tar file or destination directory does not exist.
    """
    # Ensure dest_path exists and is a directory
    if not os.path.isdir(dest_path):
        try:
            os.makedirs(dest_path)
        except Exception:
            return False
    
    # Create a temporary directory for extraction to prevent writing outside dest_path
    # We will use a subdirectory of dest_path for the actual extraction buffer
    safe_dest = os.path.join(dest_path, ".safe_extract")
    if os.path.exists(safe_dest):
        shutil.rmtree(safe_dest)
    os.makedirs(safe_dest)
    
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Validate all members before extraction
            for member in tar.getmembers():
                # Check for symbolic links
                if member.issym():
                    raise ValueError(f"Symbolic link found in archive: {member.name}")
                # Check for hard links
                if member.islnk():
                    raise ValueError(f"Hard link found in archive: {member.name}")
                
                # Calculate the target path for the member
                if member.isdir():
                    target_path = os.path.join(safe_dest, member.name)
                else:
                    target_path = os.path.join(safe_dest, member.name)
                    # Ensure parent directory exists
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                
                # Resolve the target path to check for path traversal
                resolved_target = os.path.normpath(target_path)
                
                # Ensure the resolved path is within dest_path
                if not resolved_target.startswith(os.path.normpath(dest_path)):
                    raise ValueError(f"Path traversal detected for member: {member.name}")
                
                # Also check if the member name itself starts with a path separator
                if member.name.startswith(os.sep) or (os.sep in member.name and not member.name.startswith('.')):
                    raise ValueError(f"Invalid member name with path separator: {member.name}")
            
            # Extract members to the safe directory
            tar.extractall(path=safe_dest)
            
            # Move extracted files to the final destination
            for root, dirs, files in os.walk(safe_dest):
                # Remove the safe_dest directory and its contents
                shutil.rmtree(safe_dest)
                
                # Move all items from safe_dest to dest_path
                # Calculate relative path from safe_dest to dest_path
                rel_path = os.path.relpath(root, safe_dest)
                dest_root = os.path.join(dest_path, rel_path)
                
                # Create directories in dest_path if they don't exist
                os.makedirs(dest_root, exist_ok=True)
                
                # Move files
                for file in files:
                    src_file = os.path.join(root, file)
                    dst_file = os.path.join(dest_root, file)
                    shutil.move(src_file, dst_file)
                
                # Move directories
                for dir_name in dirs:
                    src_dir = os.path.join(root, dir_name)
                    dst_dir = os.path.join(dest_root, dir_name)
                    shutil.move(src_dir, dst_dir)
            
            # Clean up any remaining artifacts in safe_dest
            if os.path.exists(safe_dest):
                shutil.rmtree(safe_dest)
            
            return True
            
    except (tarfile.TarError, ValueError, OSError) as e:
        # Clean up the safe directory on any error
        if os.path.exists(safe_dest):
            shutil.rmtree(safe_dest)
        raise
    except Exception as e:
        if os.path.exists(safe_dest):
            shutil.rmtree(safe_dest)
        raise
