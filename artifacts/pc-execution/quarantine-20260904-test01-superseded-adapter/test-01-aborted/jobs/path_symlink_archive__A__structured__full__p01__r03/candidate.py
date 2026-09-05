import os
import tarfile
import shutil
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to the specified destination path.
    
    This function validates all members of the tar archive before extraction.
    It rejects any symbolic links or hard links, even if their targets appear
    to be within the destination directory. Only regular files and directories
    are extracted. The function ensures that no archive member is written
    outside the dest_path directory.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory where the archive should be extracted.
        
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    try:
        # Ensure dest_path exists and is a directory
        if not os.path.isdir(dest_path):
            return False
            
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Validate all members before extracting
            for member in tar.getmembers():
                # Reject symbolic links and hard links
                if member.issym() or member.islnk():
                    continue
                
                # Calculate the full destination path for this member
                dest_member = os.path.join(dest_path, member.name)
                
                # Ensure the member name doesn't contain path traversal
                if not member.name.startswith(os.path.sep) and not member.name.startswith('..'):
                    # Check if the member would be outside dest_path
                    # We need to resolve the path and check if it's under dest_path
                    # Use os.path.normpath to handle .. components
                    normalized_dest = os.path.normpath(dest_member)
                    
                    # Ensure the normalized path is still within dest_path
                    # We check if the normalized path starts with dest_path + os.sep
                    # or equals dest_path (for the root member)
                    if not (normalized_dest == dest_path or normalized_dest.startswith(dest_path + os.sep)):
                        return False
                
                # Skip members that are not regular files or directories
                if not (member.isfile() or member.isdir()):
                    continue
            
            # If validation passes, perform the extraction
            tar.extractall(dest_path)
            
            return True
            
    except Exception:
        return False
