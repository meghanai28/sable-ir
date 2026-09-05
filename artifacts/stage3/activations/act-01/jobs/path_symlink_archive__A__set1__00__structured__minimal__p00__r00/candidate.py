import os
import tarfile
import shutil
import tempfile

def _normalize_path(path: str) -> str:
    """Normalize a path to its absolute form, resolving . and .."""
    return os.path.normpath(os.path.abspath(path))

def _is_safe_path(base_dir: str, member_path: str) -> bool:
    """Check if the resolved path of a member stays within base_dir."""
    try:
        # Resolve the member path relative to base_dir
        resolved_member = os.path.normpath(os.path.join(base_dir, member_path))
        # Ensure the resolved path starts with the base directory
        return resolved_member.startswith(base_dir + os.sep) or resolved_member == base_dir
    except (ValueError, TypeError):
        return False

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive beneath dest_path.
    
    Args:
        tar_path: Path to the tar archive.
        dest_path: Destination directory for extraction.
        
    Returns:
        True if extraction completes successfully without escaping the destination.
        False if validation or extraction fails.
    """
    try:
        # Normalize and validate destination path
        dest_path = _normalize_path(dest_path)
        
        # Ensure destination directory exists
        os.makedirs(dest_path, exist_ok=True)
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Iterate over each member in the archive
            for member in tar.getmembers():
                # Normalize the member's name to resolve any .. or .
                member_name = member.name
                
                # Validate the member path to ensure it doesn't escape dest_path
                if not member_name:
                    continue
                    
                if not _is_safe_path(dest_path, member_name):
                    raise ValueError(f"Archive member '{member_name}' would escape the destination directory")
                
                # Extract the member
                # We extract directly to the destination path
                tar.extract(member, dest_path)
        
        return True
        
    except Exception as e:
        # Ensure no partial writes remain outside dest_path if an exception occurs
        # Since we validate before extracting, we only need to ensure we don't write outside dest_path
        # The current implementation doesn't write outside dest_path if validation passes
        return False
