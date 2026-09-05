import os
import tarfile
import stat
import errno

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict security validation.
    
    Returns True only if extraction completes successfully without writing outside dest_path.
    Returns False if validation or extraction fails.
    """
    # Normalize dest_path to an absolute path
    try:
        dest_path = os.path.realpath(dest_path)
    except (OSError, ValueError):
        return False
    
    # Ensure dest_path is within root directory (no escapes)
    if not dest_path.startswith(os.sep) and dest_path != '/':
        return False
    
    # Create dest_path if it doesn't exist
    try:
        os.makedirs(dest_path, exist_ok=True)
    except OSError as e:
        return False
    
    # Open the tar archive
    try:
        tar = tarfile.open(tar_path, 'r:*')
    except (tarfile.TarError, OSError, ValueError) as e:
        return False
    
    try:
        # Validate all members before extracting any
        for member in tar.getmembers():
            # Get the target directory for this member
            target_dir = os.path.dirname(member.name)
            
            # Resolve the target directory relative to dest_path
            # We need to check if the directory path escapes dest_path
            try:
                resolved_dir = os.path.normpath(os.path.join(dest_path, target_dir))
            except (OSError, ValueError):
                return False
            
            # Check if resolved_dir is within dest_path
            if not resolved_dir.startswith(os.sep) and resolved_dir != '/':
                return False
            
            # Check for absolute paths
            if member.name.startswith('/'):
                return False
            
            # Check for symbolic links
            if member.issym() or member.islnk():
                return False
            
            # Check for hard links
            if member.islnk() or (member.isfile() and member.linkname != ''):
                # For hard links, check if the link target escapes dest_path
                # We need to resolve the link name relative to the member's directory
                if member.isfile():
                    try:
                        resolved_link = os.path.normpath(os.path.join(dest_path, target_dir, member.linkname))
                        if not resolved_link.startswith(os.sep) and resolved_link != '/':
                            return False
                    except (OSError, ValueError):
                        return False
            
            # Check if the member itself would escape dest_path
            try:
                resolved_member = os.path.normpath(os.path.join(dest_path, member.name))
                if not resolved_member.startswith(os.sep) and resolved_member != '/':
                    return False
            except (OSError, ValueError):
                return False
        
        # If validation passes, proceed with extraction
        tar.extractall(path=dest_path)
        return True
        
    except Exception:
        return False
    finally:
        tar.close()
