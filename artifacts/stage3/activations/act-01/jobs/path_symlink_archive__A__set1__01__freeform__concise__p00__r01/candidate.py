import os
import tarfile
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict security validation.
    
    Args:
        tar_path: Path to the tar archive.
        dest_path: Destination directory for extraction.
    
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    try:
        # Normalize dest_path to absolute and resolve symlinks if possible,
        # but primarily ensure it doesn't escape the root.
        dest_path = os.path.abspath(dest_path)
        
        # Check if dest_path escapes the root directory
        if not dest_path.startswith(os.sep) and dest_path != os.sep:
            # On Windows, os.sep is '\' and we need to handle it carefully
            # The check above handles Unix-like systems where root is '/'
            # For Windows, we check if it starts with a drive letter or is a valid path
            # However, the safest approach is to ensure it's an absolute path and doesn't contain '..'
            # that would resolve outside the root.
            pass
        
        # More robust check: ensure dest_path is within the root
        # On Unix, root is '/'
        # On Windows, root is 'C:/' or similar
        if os.sep == '\\':
            # Windows check: ensure it starts with a drive letter
            if not (len(dest_path) >= 2 and dest_path[1] == ':'):
                raise ValueError("dest_path must be an absolute path on Windows")
            # Check for '..' in the path components
            parts = dest_path.split(os.sep)
            if '..' in parts:
                raise ValueError("dest_path contains '..' which is unsafe")
        else:
            # Unix-like check: must start with '/'
            if not dest_path.startswith('/'):
                raise ValueError("dest_path must be an absolute path")
            # Check for '..' in the path components
            parts = dest_path.split(os.sep)
            if '..' in parts:
                raise ValueError("dest_path contains '..' which is unsafe")
        
        # Ensure dest_path exists and is a directory
        if not os.path.isdir(dest_path):
            os.makedirs(dest_path, exist_ok=True)
        
        # Open the tar archive
        with tarfile.open(tar_path, 'r:*') as tar:
            # Validate all members before extraction
            for member in tar.getnames():
                # Skip directories only if we want to extract files only,
                # but the requirement says "extract archive members", so we extract files and directories.
                # However, we must check for symbolic and hard links.
                
                # Check for symbolic links
                if member.isdir():
                    continue
                
                # Get the member's info
                info = tar.getmember(member)
                
                # Check for hard links
                if info.linkname is not None:
                    raise ValueError(f"Hard link detected: {member} -> {info.linkname}")
                
                # Check for symbolic links
                if info.issym() or info.islnk():
                    raise ValueError(f"Symbolic link detected: {member}")
                
                # Check for device files
                if info.devtype() == 'd':
                    raise ValueError(f"Device file detected: {member}")
                
                # Check for directory entries
                if info.isdir():
                    continue
                
                # Resolve the target path to check for escape
                member_path = os.path.join(dest_path, member)
                # Normalize the path to resolve any '..'
                member_path = os.path.normpath(member_path)
                
                # Check if the resolved path is within dest_path
                if not member_path.startswith(dest_path + os.sep) and member_path != dest_path:
                    raise ValueError(f"Member path escapes dest_path: {member}")
                
                # Also check for absolute paths that escape dest_path
                if os.path.isabs(member):
                    member_path = os.path.normpath(member)
                    if not member_path.startswith(dest_path + os.sep) and member_path != dest_path:
                        raise ValueError(f"Absolute member path escapes dest_path: {member}")
            
            # Now perform the extraction
            tar.extractall(path=dest_path)
            
            return True
    
    except Exception as e:
        return False
