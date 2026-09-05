import os
import tarfile
import shutil
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory.
    
    This function validates all archive members and link targets before extraction.
    It rejects symbolic links and hard links unless their fully resolved targets
    remain within the destination directory.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory where the archive should be extracted.
    
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    # Ensure the destination directory exists
    try:
        os.makedirs(dest_path, exist_ok=True)
    except OSError:
        return False

    # Open the tar file
    try:
        tar = tarfile.open(tar_path, 'r:*')
    except (tarfile.TarError, FileNotFoundError, PermissionError, OSError):
        return False

    # Validate all members and links before extraction
    members = []
    for member in tar.getmembers():
        # Resolve the target path for the member
        try:
            # Get the name of the member
            member_name = member.name
            
            # If it's a symlink, check the link target
            if member.issym() or member.islnk():
                # Get the link target
                link_target = member.linkname
                
                # Resolve the link target relative to the member's directory
                # For symlinks, the link target is relative to the member's directory
                # For hardlinks, the link target is relative to the member's directory
                if os.path.isabs(member_name):
                    # If the member name is absolute, it's invalid
                    return False
                
                # Construct the full path to the link target
                # The link target is relative to the member's directory
                member_dir = os.path.dirname(member_name)
                if member_dir:
                    resolved_link_target = os.path.normpath(os.path.join(member_dir, link_target))
                else:
                    resolved_link_target = link_target
                
                # Resolve the target path
                resolved_target = os.path.normpath(os.path.join(dest_path, resolved_link_target))
                
                # Check if the resolved target is within the destination directory
                # Use os.path.commonpath to ensure the resolved target is within dest_path
                try:
                    common_path = os.path.commonpath([dest_path, resolved_target])
                    if not common_path.startswith(dest_path.rstrip(os.sep)):
                        return False
                except ValueError:
                    # This can happen if paths are on different drives (Windows) or have different root directories
                    return False
            else:
                # For regular files and directories, check if the member name is absolute
                if os.path.isabs(member_name):
                    return False
                
                # Construct the full path to the member
                member_path = os.path.normpath(os.path.join(dest_path, member_name))
                
                # Check if the member path is within the destination directory
                try:
                    common_path = os.path.commonpath([dest_path, member_path])
                    if not common_path.startswith(dest_path.rstrip(os.sep)):
                        return False
                except ValueError:
                    return False
            
            members.append(member)
        except (ValueError, OSError):
            return False

    # Extract the archive
    try:
        # Extract all members
        for member in members:
            # Extract the member
            tar.extract(member, path=dest_path)
    except (tarfile.TarError, PermissionError, OSError):
        return False

    # Clean up
    tar.close()
    return True
