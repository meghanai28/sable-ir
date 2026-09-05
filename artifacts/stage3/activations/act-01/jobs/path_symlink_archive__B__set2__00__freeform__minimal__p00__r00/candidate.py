import os
import tarfile
import shutil
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict security checks.
    
    Args:
        tar_path: Path to the tar archive.
        dest_path: Destination directory for extraction.
        
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    # Normalize dest_path to an absolute path
    try:
        dest_path = os.path.realpath(dest_path)
    except (OSError, ValueError):
        return False

    # Check if dest_path escapes root
    if not dest_path.startswith(os.sep) and dest_path != os.sep:
        # On Windows, os.sep is '\' and root is '\'
        # On Unix, os.sep is '/' and root is '/'
        # We need to ensure it's not a relative path that could escape
        if not dest_path.startswith(os.sep):
            return False

    # Create dest_path if it doesn't exist
    try:
        os.makedirs(dest_path, exist_ok=True)
    except (OSError, ValueError):
        return False

    # Validate tar_path exists
    if not os.path.isfile(tar_path):
        return False

    # Create a temporary directory for safe extraction
    try:
        temp_dir = os.path.join(os.path.dirname(os.path.realpath(tar_path)), '.extracted_temp')
        os.makedirs(temp_dir, exist_ok=True)
    except (OSError, ValueError):
        return False

    try:
        # Extract to temporary directory first
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get all members
            members = tar.getmembers()
            
            for member in members:
                # Check if member is a directory
                if member.isdir():
                    # Create directory in temp
                    dir_path = os.path.join(temp_dir, member.name)
                    os.makedirs(dir_path, exist_ok=True)
                else:
                    # Create file in temp
                    file_path = os.path.join(temp_dir, member.name)
                    # Extract file content
                    tar.extract(member, temp_dir)
                    
                    # Check if it's a symlink
                    if member.issym():
                        # Resolve symlink target
                        link_target = os.path.join(temp_dir, member.name)
                        try:
                            link_target = os.path.realpath(link_target)
                        except (OSError, ValueError):
                            return False
                        
                        # Check if symlink target is within dest_path
                        if not link_target.startswith(os.sep) and link_target != os.sep:
                            return False
                        if not link_target.startswith(dest_path + os.sep):
                            return False
                        if link_target == dest_path:
                            return False
                        
                        # Create symlink in temp
                        os.symlink(link_target, link_target)
                    else:
                        # Check if file is within dest_path
                        file_path = os.path.join(temp_dir, member.name)
                        if not file_path.startswith(os.sep) and file_path != os.sep:
                            return False
                        if not file_path.startswith(dest_path + os.sep):
                            return False
                        if file_path == dest_path:
                            return False

            # Now move extracted files to dest_path
            for item in os.listdir(temp_dir):
                src_path = os.path.join(temp_dir, item)
                dst_path = os.path.join(dest_path, item)
                
                if os.path.isdir(src_path):
                    shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
                else:
                    shutil.copy2(src_path, dst_path)
            
            # Clean up temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            return True
            
    except (tarfile.TarError, OSError, ValueError):
        return False
    finally:
        # Ensure temp directory is cleaned up
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
