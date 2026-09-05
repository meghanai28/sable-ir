import os
import tarfile
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict path validation.
    
    Args:
        tar_path: Path to the tar archive.
        dest_path: Directory where the archive should be extracted.
        
    Returns:
        True if extraction completes successfully without writing outside dest_path.
        False if validation or extraction fails.
    """
    # Resolve the absolute path for dest_path
    try:
        dest_path = os.path.abspath(dest_path)
    except (ValueError, OSError):
        return False

    # Normalize the path to remove any trailing slashes or redundant separators
    dest_path = os.path.normpath(dest_path)

    # Ensure the destination directory exists
    try:
        os.makedirs(dest_path, exist_ok=True)
    except (OSError, ValueError):
        return False

    # Open the tar archive
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get the list of members to be extracted
            members = tar.getmembers()
            
            # Validate each member before extraction
            for member in members:
                # Calculate the full path where the member would be extracted
                full_path = os.path.normpath(os.path.join(dest_path, member.name))
                
                # Check if the path escapes the destination directory
                if not full_path.startswith(dest_path + os.sep) and full_path != dest_path:
                    # This check handles cases where the path is a prefix but not exactly the dest_path
                    # We need to ensure we don't allow paths like dest_path + os.sep + ".."
                    if full_path != dest_path and not full_path.startswith(dest_path):
                        return False
                
                # Check for symbolic links that point outside the destination
                if member.issym():
                    link_path = member.linkname
                    link_target = os.path.normpath(os.path.join(dest_path, link_path))
                    if not link_target.startswith(dest_path + os.sep) and link_target != dest_path:
                        return False
                
                # Additional check for paths with .. components
                # Normalize the member name relative to dest_path and check for ..
                rel_path = os.path.relpath(member.name, dest_path)
                if '..' in rel_path.split(os.sep):
                    return False

            # Extract the archive
            for member in members:
                # Extract the member to the validated path
                member_dir = os.path.dirname(member.name)
                if member_dir:
                    # Ensure the directory exists before extracting the file
                    try:
                        os.makedirs(os.path.join(dest_path, member_dir), exist_ok=True)
                    except (OSError, ValueError):
                        return False
                
                try:
                    tar.extract(member, path=dest_path)
                except (tarfile.TarError, OSError, ValueError):
                    return False

    except (OSError, ValueError, tarfile.TarError):
        return False

    return True
