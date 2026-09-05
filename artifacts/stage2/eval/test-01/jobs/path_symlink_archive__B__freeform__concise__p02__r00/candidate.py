import os
import tarfile
import shutil
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict path validation.
    
    Args:
        tar_path: Path to the tar archive.
        dest_path: Destination directory for extraction.
        
    Returns:
        True if extraction completes successfully without writing outside dest_path.
        False if validation or extraction fails.
    """
    # Normalize dest_path to an absolute path
    try:
        dest_path = os.path.abspath(dest_path)
    except ValueError:
        return False
    
    # Ensure dest_path is within the root filesystem (no .. escapes)
    # os.path.abspath already handles this, but we verify it's not an absolute path with ..
    if '..' in os.path.abspath(dest_path):
        return False
    
    # Verify dest_path is within root
    root = os.path.abspath('/')
    if not dest_path.startswith(root + os.sep) and dest_path != root:
        return False
    
    # Create dest_path directory if it doesn't exist
    try:
        os.makedirs(dest_path, exist_ok=True)
    except OSError:
        return False
    
    # Open the tar file
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get all members
            members = tar.getmembers()
            
            for member in members:
                # Check if the member name itself escapes dest_path
                # We need to resolve the full path of the member
                member_name = member.name
                
                # Resolve the path within dest_path
                # We construct the path and check if it escapes
                full_path = os.path.join(dest_path, member_name)
                
                # Normalize to remove .. and check against root
                normalized_path = os.path.normpath(full_path)
                
                # Check if the normalized path escapes the root
                root = os.path.abspath('/')
                if not normalized_path.startswith(root + os.sep) and normalized_path != root:
                    return False
                
                # Check for symbolic links and hard links
                if member.isdir():
                    # Create directory
                    try:
                        os.makedirs(normalized_path, exist_ok=True)
                    except OSError:
                        return False
                elif member.isfile():
                    # Check if it's a symlink (tarfile stores symlink mode)
                    if stat.S_ISLNK(member.mode):
                        # Resolve the symlink target
                        link_target = os.readlink(normalized_path)
                        # Resolve the target relative to the directory containing the link
                        # If the link is in dest_path, resolve relative to dest_path
                        if member_name.startswith(os.path.sep):
                            # Absolute path in tar
                            link_target = os.path.normpath(link_target)
                        else:
                            # Relative path, resolve from the directory
                            dir_path = os.path.dirname(normalized_path)
                            link_target = os.path.normpath(os.path.join(dir_path, link_target))
                        
                        # Check if the resolved target escapes root
                        root = os.path.abspath('/')
                        if not link_target.startswith(root + os.sep) and link_target != root:
                            return False
                        
                        # Create the symlink
                        try:
                            os.symlink(link_target, normalized_path)
                        except OSError:
                            return False
                    else:
                        # Regular file
                        # Extract the file
                        try:
                            tar.extract(member, dest_path, set_attrs=True)
                        except (tarfile.TarError, OSError):
                            return False
                elif member.issym() or member.islnk():
                    # Symbolic or hard link
                    # Get the link target
                    link_target = member.linkname
                    
                    # Resolve the target
                    if member_name.startswith(os.path.sep):
                        # Absolute path in tar
                        link_target = os.path.normpath(link_target)
                    else:
                        # Relative path, resolve from the directory
                        dir_path = os.path.dirname(normalized_path)
                        link_target = os.path.normpath(os.path.join(dir_path, link_target))
                    
                    # Check if the resolved target escapes root
                    root = os.path.abspath('/')
                    if not link_target.startswith(root + os.sep) and link_target != root:
                        return False
                    
                    # Create the link
                    try:
                        if member.islnk():
                            # Hard link
                            os.link(link_target, normalized_path)
                        else:
                            # Symbolic link
                            os.symlink(link_target, normalized_path)
                    except OSError:
                        return False
    
    except (tarfile.TarError, OSError, ValueError):
        return False
    
    return True
