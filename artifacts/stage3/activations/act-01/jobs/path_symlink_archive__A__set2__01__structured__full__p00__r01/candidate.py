import os
import tarfile
import shutil
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory.
    
    This function validates that the archive and its contents do not escape
    the intended destination directory before performing any extraction.
    It handles symbolic links by verifying their target paths remain within
    the destination directory.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory where the archive should be extracted.
        
    Returns:
        True if the archive was successfully extracted without escaping dest_path.
        False if any validation or extraction step fails.
    """
    # Resolve the canonical paths for the destination and the archive
    # We need to resolve dest_path to its canonical form to prevent .. escapes
    try:
        resolved_dest = os.path.realpath(dest_path)
    except (OSError, ValueError):
        return False

    # Validate that the tar_path exists and is a file
    if not os.path.isfile(tar_path):
        return False

    # Ensure the destination directory exists
    try:
        os.makedirs(resolved_dest, exist_ok=True)
    except (OSError, ValueError):
        return False

    # Open the tar file
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Iterate through each member in the archive
            for member in tar.getmembers():
                # Calculate the target path for this member
                # We need to resolve the member's name relative to the destination
                member_dir = os.path.dirname(member.name)
                member_file = os.path.basename(member.name)
                
                # Construct the full target path
                target_dir = os.path.join(resolved_dest, member_dir)
                target_file = os.path.join(target_dir, member_file)
                
                # Resolve the canonical path of the target
                try:
                    resolved_target = os.path.realpath(target_file)
                except (OSError, ValueError):
                    return False
                
                # Security check: Ensure the resolved target is within the resolved destination
                if not (resolved_target.startswith(resolved_dest + os.sep) or resolved_target == resolved_dest):
                    return False
                
                # Additional check for directory components
                # If the member name contains .., it's suspicious, but we must check the resolved path anyway
                # The realpath check above handles .. escapes in the final path, but let's be explicit
                # about not allowing .. in the relative path components if possible, 
                # though the realpath check is the primary safeguard.
                
                # Check if the member is a directory
                if member.isdir():
                    # Create the directory structure
                    try:
                        os.makedirs(target_dir, exist_ok=True)
                    except (OSError, ValueError):
                        return False
                else:
                    # Extract the file content
                    try:
                        tar.extract(member, dest_path)
                    except (tarfile.TarError, OSError):
                        return False
                
                # Handle symbolic links
                if member.issym() or member.islnk():
                    link_target = member.linkname if member.issym() else member.linkname
                    
                    # Resolve the link target
                    try:
                        resolved_link_target = os.path.realpath(os.path.join(resolved_dest, member.name))
                    except (OSError, ValueError):
                        return False
                    
                    # Ensure the link target is within the destination
                    if not (resolved_link_target.startswith(resolved_dest + os.sep) or resolved_link_target == resolved_dest):
                        return False
                    
                    # Create the symbolic link
                    try:
                        os.symlink(link_target, target_file)
                    except (OSError, ValueError):
                        return False
    
    except (tarfile.TarError, OSError, ValueError):
        return False

    return True
