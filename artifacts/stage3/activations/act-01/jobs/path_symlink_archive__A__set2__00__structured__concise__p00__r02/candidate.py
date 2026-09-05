import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory for extraction.
    
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    # Normalize and resolve the destination root to prevent directory traversal
    try:
        dest_path = os.path.normpath(dest_path)
        dest_root = os.path.abspath(dest_path)
    except (ValueError, OSError):
        return False

    # Validate that tar_path exists and is accessible
    try:
        if not os.path.isfile(tar_path):
            return False
        tar_stat = os.stat(tar_path)
        if not os.access(tar_path, os.R_OK):
            return False
    except (OSError, ValueError):
        return False

    # Open the tar file and validate members
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Check all members before extraction
            for member in tar.getmembers():
                # Calculate the destination path for this member
                member_dest = os.path.normpath(os.path.join(dest_root, member.name))
                
                # Resolve the absolute path to check for traversal
                resolved_member_dest = os.path.abspath(member_dest)
                
                # Ensure the member's destination is within the allowed dest_root
                if not resolved_member_dest.startswith(dest_root + os.sep) and resolved_member_dest != dest_root:
                    return False

            # Extract the archive
            tar.extractall(dest_path)
            return True
            
    except (tarfile.TarError, OSError, ValueError):
        return False
