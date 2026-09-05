import os
import tarfile
import shutil
import tempfile
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory.
    
    Returns True on complete success, False on any failure (including validation or extraction).
    Raises an exception if the destination path is absolute or attempts to escape the destination.
    """
    # Resolve and normalize the destination path
    try:
        dest_path = os.path.realpath(dest_path)
    except ValueError:
        return False
    
    # Check if dest_path is absolute
    if os.path.isabs(dest_path):
        raise ValueError("Destination path must be relative to the current working directory")
    
    # Create the destination directory if it doesn't exist
    os.makedirs(dest_path, exist_ok=True)
    
    # Open the tar file
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get the list of members
            members = tar.getmembers()
            
            # Validate all members before extraction
            for member in members:
                # Check for symbolic links
                if member.issym():
                    return False
                
                # Check for hard links
                if member.issym() or member.islnk():
                    return False
                
                # Resolve the target path for the member
                # If it's a symlink, we already checked above, but for safety:
                if member.isdir() or member.isfile():
                    # Resolve the member's name relative to the archive root
                    member_path = os.path.join(dest_path, member.name)
                    
                    # Normalize the path to check for .. escapes
                    normalized_path = os.path.normpath(member_path)
                    
                    # Ensure the normalized path is within dest_path
                    # We use os.path.commonpath to verify containment
                    common = os.path.commonpath([dest_path, normalized_path])
                    if common != dest_path:
                        return False
            
            # Extract the archive
            for member in members:
                # Skip symlinks and hardlinks as per requirements
                if member.issym() or member.islnk():
                    continue
                
                # Extract the member
                tar.extract(member, dest_path)
            
            return True
            
    except Exception as e:
        return False
