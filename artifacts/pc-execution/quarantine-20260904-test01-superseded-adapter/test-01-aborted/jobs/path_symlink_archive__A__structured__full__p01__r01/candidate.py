import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory, rejecting symbolic and hard links.
    Returns True only if extraction completes successfully without writing outside dest_path.
    """
    try:
        # Ensure dest_path exists and is a directory
        if not os.path.isdir(dest_path):
            return False
        
        # Create dest_path if it doesn't exist (but ensure it's a directory)
        if not os.path.exists(dest_path):
            os.makedirs(dest_path)
        
        with tarfile.open(tar_path, 'r:*') as tar:
            # First, validate all members to ensure no unsafe operations will occur
            for member in tar.getmembers():
                # Skip if the member is a symlink or hardlink
                if member.issym() or member.islnk():
                    return False
                
                # Calculate the full destination path for this member
                # Use member.name as the relative path from the archive root
                member_dir = os.path.dirname(member.name)
                member_file = os.path.basename(member.name)
                
                # Construct the absolute path where the member would be extracted
                # We must ensure this path is under dest_path
                if member_dir:
                    safe_dest = os.path.normpath(os.path.join(dest_path, member_dir))
                else:
                    safe_dest = dest_path
                
                # Check if the directory part exists in our controlled path
                # We need to ensure we don't escape the destination directory
                # by checking if the normalized path starts with the dest_path (with trailing slash)
                dest_path_normalized = os.path.normpath(dest_path) + os.sep
                if not safe_dest.startswith(dest_path_normalized):
                    return False
                
                # Additional check: ensure no .. components escape the destination
                # by verifying the path is within the allowed directory tree
                try:
                    os.makedirs(safe_dest, exist_ok=True)
                except Exception:
                    return False
            
            # If validation passes, proceed with extraction
            # Use extract() with error handling to ensure no side effects
            try:
                tar.extractall(path=dest_path)
                return True
            except Exception:
                return False
                
    except Exception:
        return False
