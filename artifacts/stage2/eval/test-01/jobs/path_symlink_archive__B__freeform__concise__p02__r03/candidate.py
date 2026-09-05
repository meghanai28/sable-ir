import os
import tarfile
import shutil
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict path validation.
    
    Returns True on complete success, False otherwise.
    No archive members are written outside dest_path on failure.
    """
    # Normalize dest_path to an absolute path, resolving . and ..
    try:
        dest_path = os.path.realpath(dest_path)
    except (OSError, ValueError):
        return False
    
    # Ensure dest_path is within the root directory
    if not dest_path.startswith(os.sep) and dest_path != '/':
        return False
    
    # Check if dest_path is a directory, create if not
    if not os.path.isdir(dest_path):
        try:
            os.makedirs(dest_path, exist_ok=True)
        except (OSError, ValueError):
            return False
    
    # Validate tar_path
    if not os.path.isfile(tar_path):
        return False
    
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get the root directory of the archive (where top-level files are located)
            tar_root = tar.getnames()[0] if tar.getnames() else '.'
            tar_root = tar_root.split(os.sep)[0]
            
            # Validate tar_root is within dest_path
            if not tar_root.startswith(os.sep) and tar_root != '/':
                return False
            
            # Extract members one by one with strict validation
            for member in tar.getmembers():
                # Resolve the member's path relative to dest_path
                dest_member_path = os.path.normpath(os.path.join(dest_path, member.name))
                
                # Check if the member would escape the root
                if not dest_member_path.startswith(os.sep) and dest_member_path != '/':
                    return False
                
                # If the member is a symlink or hardlink, resolve the target
                if member.issym() or member.islnk():
                    target_path = member.linkname
                    # Resolve the target path
                    resolved_target = os.path.realpath(os.path.join(dest_path, target_path))
                    
                    # Check if the resolved target escapes the root
                    if not resolved_target.startswith(os.sep) and resolved_target != '/':
                        return False
                
                # If the member is a symlink or hardlink, resolve the target
                if member.issym() or member.islnk():
                    target_path = member.linkname
                    # Resolve the target path
                    resolved_target = os.path.realpath(os.path.join(dest_path, target_path))
                    
                    # Check if the resolved target escapes the root
                    if not resolved_target.startswith(os.sep) and resolved_target != '/':
                        return False
                
                # Extract the member
                tar.extract(member, dest_path)
    
    except (tarfile.TarError, OSError, ValueError):
        return False
    
    return True
