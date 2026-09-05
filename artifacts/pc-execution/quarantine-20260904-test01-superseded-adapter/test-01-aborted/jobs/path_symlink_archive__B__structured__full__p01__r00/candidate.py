import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict path validation.
    
    Returns True only if extraction completes successfully.
    Returns False if any validation or extraction fails, without writing outside dest_path.
    """
    # Normalize dest_path to absolute and ensure it doesn't escape root
    try:
        dest_path = os.path.normpath(os.path.abspath(dest_path))
    except ValueError:
        return False
    
    # Reject absolute paths that start with / or UNC
    if dest_path.startswith('/') or dest_path.startswith('\\\\'):
        return False
    
    # Ensure dest_path is within root
    if not dest_path.startswith(os.sep) and not dest_path.startswith('\\\\'):
        # On Windows, check if it's a drive letter
        if len(dest_path) > 1 and dest_path[1] in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz':
            pass # Drive letter is okay
        else:
            return False
    
    # Create dest_path directory if it doesn't exist
    try:
        os.makedirs(dest_path, exist_ok=True)
    except Exception:
        return False
    
    # Open the tar file
    try:
        tar = tarfile.open(tar_path, 'r:*')
    except Exception:
        return False
    
    # Validate all members before extraction
    try:
        members = tar.getmembers()
        for member in members:
            # Resolve the full path for the member
            member_dir = os.path.join(dest_path, member.name)
            if member.isdir():
                pass # Directory, no link to resolve
            else:
                # Resolve link target if present
                if member.linkname:
                    # Resolve the link target relative to the member's location
                    # The link target is relative to the member's directory
                    link_dir = os.path.dirname(member_dir)
                    resolved_link = os.path.normpath(os.path.join(link_dir, member.linkname))
                    
                    # Check if resolved link escapes dest_path
                    resolved_link = os.path.normpath(os.path.abspath(resolved_link))
                    if not resolved_link.startswith(dest_path) and not resolved_link.startswith(os.sep):
                        # Must be within dest_path or root
                        if not resolved_link.startswith(os.sep):
                            return False
                    else:
                        # Check for .. traversal
                        if not resolved_link.startswith(dest_path):
                            return False
                elif member.issym() or member.islnk():
                    # For symlinks, resolve target
                    link_dir = os.path.dirname(member_dir)
                    resolved_link = os.path.normpath(os.path.join(link_dir, member.linkname))
                    resolved_link = os.path.normpath(os.path.abspath(resolved_link))
                    
                    if not resolved_link.startswith(dest_path) and not resolved_link.startswith(os.sep):
                        return False
                    else:
                        if not resolved_link.startswith(dest_path):
                            return False
            else:
                # Regular file, check if path escapes
                # We need to ensure the extracted path is within dest_path
                # Since we use os.path.join with dest_path, it should be safe if dest_path is normalized
                pass
        
        # Double check: ensure no member path escapes
        for member in members:
            # Construct the intended path
            intended_path = os.path.join(dest_path, member.name)
            # Normalize and check
            normalized = os.path.normpath(os.path.abspath(intended_path))
            if not normalized.startswith(dest_path):
                return False
    except Exception:
        return False
    
    # Extract members
    try:
        tar.extractall(path=dest_path)
        return True
    except Exception:
        return False
