import os
import tarfile
import shutil
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination path with strict security validation.
    
    Returns:
        True if extraction completes successfully.
        False if any validation or extraction fails.
    """
    # Validate dest_path is not absolute
    if os.path.isabs(dest_path):
        raise ValueError("Destination path must be relative")
    
    # Resolve and normalize the destination path
    try:
        resolved_dest = os.path.realpath(os.path.join(os.getcwd(), dest_path))
    except (OSError, ValueError):
        return False
    
    # Create the destination directory if it doesn't exist
    try:
        os.makedirs(resolved_dest, exist_ok=True)
    except OSError:
        return False
    
    # Open the tar file
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Validate all members before extraction
            for member in tar.getmembers():
                # Check if member is a directory
                if member.isdir():
                    continue
                
                # Check if member is a symlink
                if member.issym():
                    # Resolve the symlink target
                    try:
                        link_target = member.linkname
                        # Check if target is absolute
                        if os.path.isabs(link_target):
                            return False
                        # Resolve the target relative to the archive's location
                        # The archive's location is the directory containing tar_path
                        archive_dir = os.path.dirname(os.path.abspath(tar_path))
                        resolved_link_target = os.path.normpath(os.path.join(archive_dir, link_target))
                        
                        # Check if resolved target is outside dest_path
                        if not resolved_link_target.startswith(os.path.normpath(resolved_dest)):
                            return False
                    except (OSError, ValueError):
                        return False
                    continue
                
                # Check if member is a hardlink
                if member.islnk():
                    # Resolve the hardlink target
                    try:
                        link_target = member.linkname
                        # Check if target is absolute
                        if os.path.isabs(link_target):
                            return False
                        # Resolve the target relative to the archive's location
                        archive_dir = os.path.dirname(os.path.abspath(tar_path))
                        resolved_link_target = os.path.normpath(os.path.join(archive_dir, link_target))
                        
                        # Check if resolved target is outside dest_path
                        if not resolved_link_target.startswith(os.path.normpath(resolved_dest)):
                            return False
                    except (OSError, ValueError):
                        return False
                    continue
                
                # Check if member is a regular file
                if not member.isfile():
                    return False
                
                # Check if member name contains .. or starts with ..
                member_name = member.name
                if '..' in member_name or member_name.startswith('..'):
                    return False
                
                # Check if member name is absolute
                if os.path.isabs(member.name):
                    return False
    
    except (tarfile.TarError, OSError):
        return False
    
    # Perform the extraction
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Extract with safety checks
            for member in tar.getmembers():
                # Skip validation again during extraction to ensure consistency
                # Extract the member
                tar.extract(member, path=resolved_dest)
    except (tarfile.TarError, OSError):
        return False
    
    return True
