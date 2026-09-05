import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory, ensuring no files escape
    the destination directory by validating paths of all archive members.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory path.
    
    Returns:
        True if extraction completes successfully without writing outside dest_path.
        False if any validation or extraction fails.
    """
    # Normalize the destination path to remove any trailing slashes or relative components
    # We will resolve it to an absolute path to prevent directory traversal attacks
    try:
        dest_path = os.path.abspath(dest_path)
        if not os.path.isdir(dest_path):
            os.makedirs(dest_path, exist_ok=True)
    except (OSError, ValueError):
        return False

    # Open the tar file
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Iterate over each member in the tar archive
            for member in tar.getmembers():
                # Resolve the member's name to an absolute path
                # We need to ensure the member's name does not escape the dest_path
                member_name = member.name
                
                # Check for null bytes or other unsafe characters
                if '\0' in member_name:
                    return False
                
                # Calculate the absolute path where the member would be extracted
                # Use os.path.join to handle the path correctly
                member_dest = os.path.join(dest_path, member_name)
                
                # Normalize the member_dest to remove any .. or . components
                # This helps in detecting directory traversal attempts
                member_dest = os.path.normpath(member_dest)
                
                # Ensure the member_dest is within the dest_path
                if not member_dest.startswith(os.path.normpath(dest_path) + os.sep) and member_dest != os.path.normpath(dest_path):
                    return False
                
                # Check for symbolic links or hard links
                if member.isdir:
                    # Create the directory
                    try:
                        os.makedirs(member_dest, exist_ok=True)
                    except (OSError, ValueError):
                        return False
                elif member.isfile:
                    # Extract the file
                    try:
                        tar.extract(member, dest_path)
                    except (OSError, ValueError):
                        return False
                elif member.issym() or member.islnk():
                    # Handle symbolic links or hard links
                    # Check the link target
                    if member.issym():
                        link_target = member.linkname
                    else:
                        link_target = member.linkname
                    
                    # Resolve the link target
                    link_target = os.path.normpath(os.path.join(dest_path, link_target))
                    
                    # Ensure the link target is within the dest_path
                    if not link_target.startswith(os.path.normpath(dest_path) + os.sep) and link_target != os.path.normpath(dest_path):
                        return False
                    
                    # Extract the link
                    try:
                        if member.issym():
                            os.symlink(link_target, member_dest)
                        else:
                            os.link(link_target, member_dest)
                    except (OSError, ValueError):
                        return False
                else:
                    # Skip other types or handle them as appropriate
                    pass
    except (tarfile.TarError, OSError, ValueError):
        return False

    return True
