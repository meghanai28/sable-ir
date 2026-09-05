import os
import tarfile
import shutil
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict security guards.
    
    Rules:
    - Reject any symbolic links or hard links, even if targets appear to stay within dest_path.
    - Only extract regular files and directories.
    - All validation must occur before any file I/O.
    - Return True only if all members pass validation and extraction completes successfully.
    - Return False if any member fails validation or extraction, and never write outside dest_path.
    """
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Create the destination directory if it doesn't exist
            os.makedirs(dest_path, exist_ok=True)
            
            # Get the absolute path of the destination directory
            dest_dir = os.path.abspath(dest_path)
            
            # Process each member
            for member in tar.getmembers():
                # Check if the member is a symbolic link or hard link
                if member.issym() or member.islnk():
                    return False
                
                # Check if the member is a regular file or directory
                if not (member.isfile() or member.isdir()):
                    return False
                
                # Calculate the absolute path of the member's target
                if member.isdir():
                    target_path = os.path.join(dest_dir, member.name)
                else:
                    target_path = os.path.join(dest_dir, member.name)
                
                # Normalize the path to resolve any symlinks or .. components
                normalized_target = os.path.normpath(target_path)
                
                # Ensure the normalized path is within the destination directory
                if not normalized_path.startswith(dest_dir):
                    return False
                
                # Extract the member
                tar.extract(member, dest_path)
            
            return True
            
    except Exception:
        return False

def _normalized_path(path: str) -> str:
    """
    Helper function to normalize a path.
    """
    return os.path.normpath(path)
