import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory with strict path validation.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory where the archive should be extracted.
        
    Returns:
        True if extraction completes successfully with all members staying within dest_path.
        False if any validation or extraction fails, without writing outside dest_path.
    """
    try:
        # Resolve and normalize the destination path
        dest_path = os.path.realpath(dest_path)
        if not os.path.isdir(dest_path):
            return False
        
        # Open the tar file
        tar = tarfile.open(tar_path, 'r:*')
        
        try:
            # Extract each member with validation
            for member in tar.getmembers():
                # Skip directories to avoid creating directory structure outside dest_path
                if member.isdir():
                    continue
                
                # Resolve the member's name relative to dest_path
                member_name = os.path.join(dest_path, member.name)
                
                # Normalize the member name to prevent directory traversal
                member_name = os.path.normpath(member_name)
                
                # Check if the member name contains '..'
                if '..' in member_name:
                    return False
                
                # Check if the member name starts with '..'
                if member_name.startswith('..'):
                    return False
                
                # Check if the member name is an absolute path
                if os.path.isabs(member.name):
                    return False
                
                # Check if the resolved path is within dest_path
                if not member_name.startswith(dest_path + os.sep) and member_name != dest_path:
                    return False
                
                # Extract the member
                tar.extract(member, dest_path)
        
        finally:
            tar.close()
        
        return True
        
    except Exception:
        return False
