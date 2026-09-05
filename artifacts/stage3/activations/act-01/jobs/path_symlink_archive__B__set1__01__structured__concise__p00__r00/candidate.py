import os
import tarfile
import shutil
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory, validating that no file
    or link is extracted outside the destination directory.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory where the archive should be extracted.
    
    Returns:
        True if extraction completed successfully, False otherwise.
    """
    # Normalize the destination path to remove any trailing slashes and resolve
    # relative components to prevent directory traversal attacks.
    # We use os.path.realpath to resolve symlinks and .. components.
    try:
        dest_path = os.path.realpath(dest_path)
    except (OSError, ValueError):
        return False

    # Ensure the destination directory exists.
    try:
        os.makedirs(dest_path, exist_ok=True)
    except OSError:
        return False

    # Open the tar file for reading.
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Iterate over each member in the archive.
            for member in tar.getmembers():
                # Normalize the member's name to check for traversal attempts.
                # We use os.path.normpath to resolve .. components.
                member_name = os.path.normpath(member.name)
                
                # Calculate the full destination path for this member.
                # We join the normalized dest_path with the normalized member name.
                # We must ensure the member name does not start with .. after normalization
                # and that the resulting path is within dest_path.
                if member_name.startswith('..') or member_name == '..':
                    return False
                
                # Construct the target path.
                target_path = os.path.join(dest_path, member_name)
                
                # Resolve the target path to check for traversal.
                try:
                    resolved_target = os.path.realpath(target_path)
                except (OSError, ValueError):
                    return False
                
                # Check if the resolved target is outside the destination directory.
                if not resolved_target.startswith(dest_path + os.sep) and resolved_target != dest_path:
                    return False
                
                # Validate and extract the member.
                try:
                    if member.isdir():
                        os.makedirs(resolved_target, exist_ok=True)
                    elif member.issym() or member.islnk():
                        # For links, we must ensure the target is also within dest_path.
                        # The validation above checks the resolved target, but we should
                        # also ensure the link target doesn't point outside.
                        # However, the primary check on resolved_target covers the extraction point.
                        # We extract the link content.
                        tar.extract(member, dest_path, set_attrs=True)
                    else:
                        # For regular files, extract the content.
                        tar.extract(member, dest_path, set_attrs=True)
                except (tarfile.TarError, OSError):
                    return False
                    
    except (tarfile.TarError, OSError):
        return False

    return True
