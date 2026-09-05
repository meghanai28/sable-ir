import os
import tarfile
import tempfile
import shutil

def _normalize_path(path: str) -> str:
    """Normalize a path to an absolute path without resolving symlinks."""
    if not os.path.isabs(path):
        path = os.path.abspath(path)
    return os.path.normpath(path)

def _is_within_root(root: str, target: str) -> bool:
    """Check if target is within root directory."""
    try:
        return target.startswith(os.path.normpath(root) + os.sep) or target == os.path.normpath(root)
    except ValueError:
        return False

def _resolve_symlink_target(link_path: str) -> str:
    """Resolve the target of a symbolic link."""
    try:
        return os.readlink(link_path)
    except (OSError, ValueError):
        return None

def _check_path_safety(dest_path: str, member_path: str, member_link_target: str) -> bool:
    """
    Check if a tar member's path or link target is safe relative to dest_path.
    Returns True if safe, False otherwise.
    """
    # Check the member path itself
    member_abs = os.path.normpath(os.path.join(dest_path, member_path))
    if not _is_within_root(dest_path, member_abs):
        return False

    # Check link targets if present
    if member_link_target is not None:
        link_abs = os.path.normpath(os.path.join(dest_path, member_link_target))
        if not _is_within_root(dest_path, link_abs):
            return False
    
    return True

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive beneath dest_path.
    Returns True on complete success, False on any failure or unsafe path.
    """
    # Normalize dest_path immediately
    normalized_dest = _normalize_path(dest_path)
    
    # Check if dest_path escapes root
    if not _is_within_root('/', normalized_dest):
        return False

    # Open the tar file
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get all members first
            members = tar.getmembers()
            
            # Validate all members before extraction
            for member in members:
                # Skip directory entries (end with /)
                if member.name.endswith('/'):
                    continue
                
                # Resolve symlink targets if the member is a symlink
                link_target = None
                if member.issym() or member.islnk():
                    link_target = _resolve_symlink_target(member.name)
                
                # Check safety
                if not _check_path_safety(normalized_dest, member.name, link_target):
                    return False
            
            # Extract members
            for member in members:
                if member.isdir():
                    # Create directory
                    dir_path = os.path.normpath(os.path.join(normalized_dest, member.name))
                    os.makedirs(dir_path, exist_ok=True)
                else:
                    # Extract file
                    member_path = os.path.normpath(os.path.join(normalized_dest, member.name))
                    os.makedirs(os.path.dirname(member_path), exist_ok=True)
                    with open(member_path, 'wb') as f:
                        f.write(tar.extractfile(member).read())
            
            return True
            
    except Exception:
        return False
