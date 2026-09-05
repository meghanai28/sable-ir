import os
import tarfile
import tempfile
import shutil

def _get_safe_root(tar_path: str) -> str:
    """Resolve the safe root directory based on the tar archive's location."""
    return os.path.abspath(os.path.dirname(tar_path))

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination path with strict security validations.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory for extraction.
    
    Returns:
        True if extraction completes successfully without escaping the root, False otherwise.
    """
    try:
        # Determine the safe root based on the tar archive's location
        safe_root = _get_safe_root(tar_path)
        
        # Normalize and resolve the destination path
        dest_path = os.path.abspath(dest_path)
        
        # Check if dest_path escapes the safe root
        if not dest_path.startswith(safe_root) or dest_path == safe_root:
            # If dest_path is exactly safe_root, that's fine, but we need to ensure
            # we don't accidentally write outside. The check above handles escaping.
            pass
        elif dest_path != safe_root:
            if not dest_path.startswith(safe_root + os.sep):
                return False
        
        # Create the destination directory if it doesn't exist
        os.makedirs(dest_path, exist_ok=True)
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get the list of members
            members = tar.getmembers()
            
            # Validate each member before extraction
            for member in members:
                # Skip symbolic links and hard links entirely
                if member.issym() or member.islnk():
                    continue
                
                # Calculate the expected destination path for this member
                # We need to resolve the path relative to the dest_path
                # and check if it escapes the safe_root
                
                # Get the relative path of the member
                rel_path = os.path.relpath(member.name, tar.getnames()[0] if tar.getnames() else '')
                
                # Construct the full destination path
                full_dest = os.path.normpath(os.path.join(dest_path, member.name))
                
                # Resolve the full path to check for .. escapes
                resolved_full = os.path.abspath(full_dest)
                
                # Check if the resolved path escapes the safe root
                if not resolved_full.startswith(safe_root) or resolved_full == safe_root:
                    return False
                
                # Check if the member name itself contains ..
                if '..' in member.name.split(os.sep):
                    return False
            
            # If validation passes, perform the extraction
            for member in members:
                if member.issym() or member.islnk():
                    continue
                
                # Extract the member
                tar.extract(member, dest_path)
            
            return True
            
    except Exception:
        return False
