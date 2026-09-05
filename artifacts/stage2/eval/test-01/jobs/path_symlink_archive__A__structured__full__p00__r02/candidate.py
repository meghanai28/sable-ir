import os
import tarfile
import shutil
import tempfile

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination path with strict security checks.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory where the archive should be extracted.
    
    Returns:
        True if extraction completes successfully, False otherwise.
        No archive members are written outside dest_path on failure.
    """
    try:
        # Resolve the canonical paths to prevent path traversal attacks
        # We use os.path.realpath to resolve symlinks and normalize paths
        real_tar_path = os.path.realpath(tar_path)
        
        # Create the destination directory if it doesn't exist
        os.makedirs(dest_path, exist_ok=True)
        
        # Get the canonical path of the destination
        real_dest_path = os.path.realpath(dest_path)
        
        # Open the tar file
        with tarfile.open(tar_path) as tar:
            # Get all members from the tar archive
            members = tar.getmembers()
            
            # Validate each member before extraction
            for member in members:
                # Skip symbolic links and hard links entirely
                if member.issym() or member.islnk():
                    continue
                
                # Calculate the target path for the member
                # For directories, the target is the directory itself
                # For files, the target is the file within the directory
                if member.isdir():
                    target_path = os.path.join(real_dest_path, member.name)
                else:
                    target_path = os.path.join(real_dest_path, member.name)
                
                # Resolve the target path to check for path traversal
                try:
                    resolved_target = os.path.realpath(target_path)
                except (OSError, ValueError):
                    # If we can't resolve the path, it's unsafe
                    return False
                
                # Check if the resolved target is within the destination directory
                if not resolved_target.startswith(real_dest_path + os.sep) and resolved_target != real_dest_path:
                    return False
            
            # Extract the archive members
            for member in members:
                # Skip symbolic links and hard links
                if member.issym() or member.islnk():
                    continue
                
                # Extract the member
                try:
                    tar.extract(member, path=real_dest_path)
                except (tarfile.TarError, OSError):
                    return False
        
        return True
    
    except Exception:
        return False
