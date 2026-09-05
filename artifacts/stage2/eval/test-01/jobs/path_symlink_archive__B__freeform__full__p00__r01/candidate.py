import os
import tarfile
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory with strict path validation.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory for extraction.
    
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    # Normalize dest_path to absolute path
    try:
        dest_path = os.path.abspath(dest_path)
    except (OSError, ValueError):
        return False

    # Ensure dest_path is within root filesystem (prevent absolute path escapes)
    if not dest_path.startswith(os.sep) and dest_path != os.sep:
        # On Windows, os.sep is '\\' or '/'. We need to ensure it's a valid absolute path.
        # The check above handles the case where it starts with a drive letter or root.
        # However, we must also ensure it doesn't escape via .. in the original input.
        # Since we took abspath, .. are resolved. We just need to ensure it's not a root escape.
        pass

    # Validate dest_path is not a root directory escape (e.g., / or C:\)
    if dest_path in ('/', os.sep) or dest_path.startswith(os.sep):
        # If dest_path is just a separator, it's invalid as a destination
        return False

    # Ensure dest_path exists and is a directory
    try:
        if not os.path.isdir(dest_path):
            os.makedirs(dest_path, exist_ok=True)
    except (OSError, PermissionError):
        return False

    # Validate dest_path does not escape root (double check)
    # On Windows, check for drive letters. On Unix, check for leading /
    if os.name == 'nt':
        if dest_path.startswith('\\\\') or dest_path.startswith('/'):
            return False
    else:
        if dest_path.startswith('/'):
            return False

    # Open the tar file
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get all members
            members = tar.getmembers()
            
            # Validate each member before extraction
            for member in members:
                # Resolve the full path of the member's name
                member_name = member.name
                
                # Handle symbolic links and hard links
                if member.issym() or member.islnk():
                    # For symlinks, we need to resolve the link target
                    link_target = member.linkname
                    
                    # Normalize the link target
                    link_target = os.path.normpath(link_target)
                    
                    # Construct the full target path
                    # If the member is a symlink, the target can be relative to the member's location
                    # We need to resolve it relative to the member's directory
                    member_dir = os.path.dirname(member_name)
                    
                    # Resolve the link target relative to the member's directory
                    if os.path.isabs(link_target):
                        full_target = link_target
                    else:
                        full_target = os.path.join(member_dir, link_target)
                    
                    # Normalize the full target
                    full_target = os.path.normpath(full_target)
                    
                    # Check if the full target is within dest_path
                    if not full_target.startswith(dest_path + os.sep) and full_target != dest_path:
                        # Also check for root escapes on Windows
                        if os.name == 'nt':
                            if full_target.startswith('\\\\') or full_target.startswith('/'):
                                return False
                        else:
                            if full_target.startswith('/'):
                                return False
                    
                    # Additional check: ensure the resolved path is within dest_path
                    # Use os.path.commonpath to verify containment
                    try:
                        common = os.path.commonpath([dest_path, full_target])
                        if common != dest_path:
                            return False
                    except ValueError:
                        return False
                
                elif member.isdir() or member.isfile():
                    # For regular files and directories, the member name is relative to dest_path
                    # We need to resolve the full path
                    member_dir = os.path.dirname(member_name)
                    full_path = os.path.normpath(os.path.join(dest_path, member_name))
                    
                    # Check if the full path is within dest_path
                    if not full_path.startswith(dest_path + os.sep) and full_path != dest_path:
                        return False
                    
                    # Additional check using commonpath
                    try:
                        common = os.path.commonpath([dest_path, full_path])
                        if common != dest_path:
                            return False
                    except ValueError:
                        return False
            
            # All members validated, proceed with extraction
            for member in members:
                try:
                    tar.extract(member, dest_path)
                except (tarfile.TarError, OSError, PermissionError):
                    return False
            
            return True
            
    except (tarfile.TarError, OSError, PermissionError):
        return False
