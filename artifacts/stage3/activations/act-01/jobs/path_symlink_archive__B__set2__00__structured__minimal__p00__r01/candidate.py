import os
import tarfile
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination path with security checks.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory for extraction.
    
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    # Normalize paths to absolute forms to prevent relative path escapes
    tar_path = os.path.abspath(tar_path)
    dest_path = os.path.abspath(dest_path)
    
    # Ensure the destination directory exists and is not a symlink to a parent directory
    if not os.path.isdir(dest_path):
        return False
    
    # Create the destination directory if it doesn't exist
    os.makedirs(dest_path, exist_ok=True)
    
    # Check if the destination path is a symlink and points outside the intended location
    dest_stat = os.stat(dest_path)
    if stat.S_ISLNK(dest_stat.st_mode):
        dest_target = os.readlink(dest_path)
        dest_resolved = os.path.normpath(os.path.join(os.path.dirname(dest_path), dest_target))
        if not dest_resolved.startswith(os.path.abspath(os.path.dirname(dest_path))):
            return False
    
    # Validate that the destination directory is within the intended scope
    # This check ensures dest_path doesn't escape the root or contain ..
    dest_resolved = os.path.abspath(dest_path)
    if not dest_resolved.startswith(os.path.abspath(os.path.dirname(dest_path))):
        return False
    
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get all members of the archive
            members = tar.getnames()
            
            # Validate each member before extraction
            for member in members:
                # Skip directories that are not explicitly requested (though standard behavior is to extract them)
                # We need to check if the member path escapes the destination
                member_path = os.path.join(dest_path, member)
                member_normalized = os.path.normpath(member_path)
                
                # Check for .. in the member path
                if '..' in member_path.split(os.sep):
                    return False
                
                # Check if the normalized path escapes the destination
                if not member_normalized.startswith(dest_resolved + os.sep):
                    return False
                
                # Check for symbolic links that would escape the destination
                if member.isdir() or member.issym():
                    if member.isfile() and member.linkname:
                        link_target = os.path.normpath(os.path.join(dest_path, member.name))
                        if not link_target.startswith(dest_resolved + os.sep):
                            return False
                    elif member.issym():
                        link_target = os.path.normpath(os.path.join(dest_path, member.name))
                        if not link_target.startswith(dest_resolved + os.sep):
                            return False
            
            # Extract the archive
            tar.extractall(path=dest_path)
            
            return True
            
    except Exception:
        return False
