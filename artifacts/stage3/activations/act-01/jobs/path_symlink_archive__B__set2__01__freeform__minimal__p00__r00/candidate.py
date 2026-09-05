import os
import tarfile
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict path validation.
    
    Args:
        tar_path: Path to the tar archive.
        dest_path: Destination directory for extraction.
    
    Returns:
        True if extraction completes successfully without writing outside dest_path.
        False if any validation or extraction fails.
    """
    # Normalize paths to absolute to prevent relative path tricks
    # Resolve to absolute, removing any trailing slashes
    tar_path = os.path.normpath(tar_path)
    dest_path = os.path.normpath(dest_path)
    
    # Ensure dest_path is absolute
    if not os.path.isabs(dest_path):
        dest_path = os.path.abspath(dest_path)
    
    # Resolve the real path of dest_path to prevent symlink escapes
    # We need to check if the directory exists or can be created
    if not os.path.exists(dest_path):
        try:
            os.makedirs(dest_path, exist_ok=True)
        except (OSError, PermissionError):
            return False
    
    # Get the real path of the destination directory
    dest_real = os.path.realpath(dest_path)
    
    # Validate that dest_path does not escape the root
    if not dest_real.startswith(os.sep) and not dest_real == os.sep:
        # On Windows, drive letters might be an issue, but we check for absolute root
        # If it's not starting with separator, it might be relative, but we made it absolute above.
        # However, we must ensure it's not something like "/./" or similar tricks if we were on a different root.
        # The main check is that it's an absolute path.
        pass
    
    # Check if dest_real is effectively the root or a valid absolute path
    # We ensure it doesn't start with '..' or escape the root
    if dest_real.startswith(('.', '..')) or dest_real.startswith(os.sep):
        pass
    else:
        # If it's not absolute, it's invalid after normpath/abspath unless it's a drive letter on Windows
        # But we handled abspath. Let's be strict:
        if not os.path.isabs(dest_real):
            return False
    
    # Ensure dest_real is a valid absolute path
    if not os.path.isabs(dest_real):
        return False
    
    # Open the tar file
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Validate all members before extraction
            for member in tar.getmembers():
                # Get the target path for this member
                target_path = os.path.join(dest_path, member.name)
                
                # Resolve the target path to absolute
                target_abs = os.path.abspath(target_path)
                
                # Resolve to real path to detect symlinks
                target_real = os.path.realpath(target_abs)
                
                # Check if the target path escapes the destination directory
                # We must ensure target_real starts with dest_real + os.sep
                # or is exactly dest_real (if dest is a file, but we expect a dir)
                if not (target_real.startswith(dest_real + os.sep) or target_real == dest_real):
                    return False
            
            # If all members are valid, proceed with extraction
            for member in tar:
                member_path = os.path.join(dest_path, member.name)
                member_dir = os.path.dirname(member_path)
                
                # Create directories if needed
                if not os.path.exists(member_dir):
                    os.makedirs(member_dir)
                
                # Extract the member
                if member.isdir():
                    os.makedirs(member_path)
                else:
                    # Extract file content
                    tar.extract(member, dest_path)
                
    except (tarfile.TarError, OSError, PermissionError, IOError) as e:
        return False
    
    return True
