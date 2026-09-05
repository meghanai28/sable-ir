import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path, rejecting symbolic links and hard links.
    Returns True on complete success, False on any failure or security violation.
    """
    # Validate dest_path: must be relative
    if os.path.isabs(dest_path):
        return False
    
    # Resolve dest_path to an absolute path for validation, but keep it relative for extraction logic
    try:
        dest_path = os.path.abspath(dest_path)
    except (OSError, ValueError):
        return False
    
    # Ensure dest_path exists and is a directory
    if not os.path.isdir(dest_path):
        return False
    
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Iterate over all members
            for member in tar.getmembers():
                # Check for symbolic links
                if member.issym():
                    return False
                
                # Check for hard links
                if member.islnk():
                    return False
                
                # Check if the member's target would be outside dest_path
                # For directories, check the path
                if member.isdir():
                    target_path = os.path.join(dest_path, member.name)
                    if not target_path.startswith(dest_path):
                        return False
                else:
                    # For files, check the directory part of the path
                    dir_path = os.path.dirname(os.path.join(dest_path, member.name))
                    if not dir_path.startswith(dest_path):
                        return False
                    # Also check the file itself
                    file_path = os.path.join(dest_path, member.name)
                    if not file_path.startswith(dest_path):
                        return False
            
            # If all checks pass, extract the archive
            tar.extractall(dest_path)
            
            return True
            
    except (tarfile.TarError, OSError, IOError):
        return False
