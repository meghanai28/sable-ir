import os
import tarfile
import shutil
import tempfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination path with strict security validation.
    
    This function:
    1. Validates that the destination path does not escape the root directory.
    2. Walks through the tar archive members, validating paths and links before extraction.
    3. Extracts only if all validations pass.
    4. Returns True on complete success, False otherwise.
    """
    # Create a temporary directory for the extraction process
    with tempfile.TemporaryDirectory() as temp_dir:
        # Copy the tar file to the temporary directory to avoid modifying the original
        tar_file_path = os.path.join(temp_dir, os.path.basename(tar_path))
        shutil.copy2(tar_path, tar_file_path)
        
        # Create the destination directory
        try:
            os.makedirs(dest_path, exist_ok=True)
        except OSError as e:
            return False
        
        # Validate the destination path
        if not _validate_dest_path(dest_path):
            return False
        
        # Extract the tar archive
        try:
            with tarfile.open(tar_file_path, 'r:*') as tar:
                members = tar.getmembers()
                
                for member in members:
                    # Validate the member path
                    if not _validate_member(member, dest_path):
                        return False
                    
                    # Extract the member
                    try:
                        tar.extract(member, dest_path)
                    except Exception:
                        return False
                
                return True
                
        except Exception:
            return False


def _validate_dest_path(dest_path: str) -> bool:
    """
    Validate that the destination path does not escape the root directory.
    
    Returns True if the path is valid, False otherwise.
    """
    # Normalize the destination path
    normalized_dest = os.path.normpath(dest_path)
    
    # Check if the path is absolute
    if not os.path.isabs(normalized_dest):
        return False
    
    # Ensure the path exists and is a directory
    if not os.path.isdir(normalized_dest):
        return False
    
    # Check if the path is within the root directory
    root = os.path.dirname(normalized_dest)
    if root != normalized_dest:
        return False
    
    return True


def _validate_member(member, dest_path: str) -> bool:
    """
    Validate a tar member path and links.
    
    Returns True if the member is valid, False otherwise.
    """
    # Check if the member name contains null bytes
    if '\0' in member.name:
        return False
    
    # Check if the member name is a symlink
    if member.issym() or member.islnk():
        # Check if the link target is absolute
        if member.linkname.startswith('/'):
            return False
        
        # Normalize the link target
        normalized_link = os.path.normpath(os.path.join(dest_path, member.linkname))
        
        # Check if the link target is within the destination directory
        if not normalized_link.startswith(os.path.normpath(dest_path)):
            return False
        
        # Check if the link target is a symlink
        if os.path.islink(normalized_link):
            # Check if the link target is absolute
            if os.path.isabs(normalized_link):
                return False
        
        # Check if the link target is a symlink
        if os.path.islink(normalized_link):
            # Check if the link target is within the destination directory
            if not os.path.isabs(normalized_link):
                normalized_link = os.path.normpath(os.path.join(dest_path, normalized_link))
                if not normalized_link.startswith(os.path.normpath(dest_path)):
                    return False
    
    return True
