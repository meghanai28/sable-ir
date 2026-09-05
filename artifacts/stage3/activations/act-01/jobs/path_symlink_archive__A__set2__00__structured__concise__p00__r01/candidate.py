import os
import tarfile
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory.
    
    Args:
        tar_path: Path to the tar archive.
        dest_path: Destination directory for extraction.
        
    Returns:
        True if extraction completes successfully, False otherwise.
        No files are written outside dest_path on failure.
    """
    # Normalize and resolve the destination root
    try:
        dest_path = os.path.normpath(dest_path)
        dest_root = os.path.abspath(dest_path)
    except (ValueError, OSError):
        return False

    # Normalize the tar path
    try:
        tar_path = os.path.normpath(tar_path)
    except (ValueError, OSError):
        return False

    # Check if tar file exists
    if not os.path.isfile(tar_path):
        return False

    # Check if dest_root is a directory
    if not os.path.isdir(dest_root):
        return False

    # Create dest_root if it doesn't exist
    try:
        os.makedirs(dest_root, exist_ok=True)
    except OSError:
        return False

    # Validate that dest_root doesn't escape expected boundaries (basic check)
    # In a real scenario, we might enforce dest_root is within a trusted base,
    # but here we assume dest_root is the intended target and validate against it.

    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get all members
            members = tar.getmembers()
            
            # Validate each member's destination path
            for member in members:
                # Get the target path for this member
                target_path = os.path.join(dest_root, member.name)
                
                # Resolve the target path to check for escapes
                resolved_target = os.path.normpath(target_path)
                
                # Ensure the resolved path is within dest_root
                # We use os.path.commonpath or check prefix with trailing separator
                if not (resolved_target == dest_root or resolved_target.startswith(dest_root + os.sep)):
                    return False
            
            # Extract the archive
            tar.extractall(path=dest_root)
            return True
            
    except (tarfile.TarError, OSError):
        return False
