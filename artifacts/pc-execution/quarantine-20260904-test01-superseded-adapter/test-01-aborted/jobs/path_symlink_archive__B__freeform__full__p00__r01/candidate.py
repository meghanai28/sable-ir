import os
import tarfile
import shutil
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory with strict security validation.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory where the archive will be extracted.
        
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    # Validate and resolve paths
    try:
        tar_path = os.path.realpath(tar_path)
        dest_path = os.path.realpath(dest_path)
    except (ValueError, OSError):
        return False
    
    # Ensure destination directory exists and is a directory
    if not os.path.isdir(dest_path):
        return False
    
    # Create destination directory if it doesn't exist
    try:
        os.makedirs(dest_path, exist_ok=True)
    except OSError:
        return False
    
    # Open the tar file
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Iterate over all members in the tar file
            for member in tar.getmembers():
                # Skip directories to avoid creating the directory structure prematurely
                # We only extract files and handle links explicitly
                if member.isdir():
                    continue
                
                # Check if the member is a symlink or hardlink
                if member.issym() or member.islnk():
                    # Resolve the link target
                    try:
                        link_target = member.linkname
                        # Normalize the link target
                        link_target = os.path.normpath(link_target)
                        
                        # Check if the link target is outside the destination directory
                        # We need to resolve the link target relative to the archive's root
                        # and then check if it escapes the destination
                        if not link_target.startswith(os.sep):
                            link_target = os.path.join(dest_path, link_target)
                        else:
                            link_target = os.path.join(dest_path, link_target)
                        
                        # Normalize again to handle .. and .
                        link_target = os.path.normpath(link_target)
                        
                        # Check if the resolved link target is inside the destination directory
                        if not link_target.startswith(os.path.realpath(dest_path) + os.sep) and link_target != os.path.realpath(dest_path):
                            return False
                    except (ValueError, OSError):
                        return False
                
                # Check if the member is a regular file or directory
                if not member.isfile() and not member.isdir() and not member.issym() and not member.islnk():
                    # Skip unknown member types
                    continue
                
                # Check if the member's name starts with the destination path
                # This prevents extraction to arbitrary locations
                member_name = member.name
                
                # Normalize the member name
                member_name = os.path.normpath(member_name)
                
                # Check if the member name is inside the destination directory
                if not member_name.startswith(os.sep):
                    member_name = os.path.join(dest_path, member_name)
                else:
                    member_name = os.path.join(dest_path, member_name)
                
                # Normalize again to handle .. and .
                member_name = os.path.normpath(member_name)
                
                # Check if the resolved member name is inside the destination directory
                if not member_name.startswith(os.path.realpath(dest_path) + os.sep) and member_name != os.path.realpath(dest_path):
                    return False
                
                # Extract the member
                try:
                    tar.extract(member, dest_path)
                except (tarfile.TarError, OSError):
                    return False
    
    except (tarfile.TarError, OSError):
        return False
    
    return True
