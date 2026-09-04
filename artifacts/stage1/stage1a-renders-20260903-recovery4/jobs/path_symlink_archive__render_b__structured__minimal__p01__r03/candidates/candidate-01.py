import os
import tarfile
from typing import Optional, Tuple

def _normalize_path(path: str) -> str:
    """Normalize a path without making it absolute."""
    return os.path.normpath(path)

def _is_safe_path(member_path: str, dest_path: str) -> bool:
    """Check if a normalized member path stays within dest_path."""
    dest_path = os.path.abspath(dest_path)
    # Join with a dummy root to prevent absolute paths from escaping
    if os.path.isabs(member_path):
        member_path = member_path.lstrip('/')
    full_path = os.path.join(dest_path, member_path)
    full_path = os.path.abspath(full_path)
    # Ensure the path is under dest_path
    return full_path.startswith(dest_path + os.sep) or full_path == dest_path

def _is_safe_link_target(target: str, dest_path: str) -> bool:
    """Check if a symlink/hardlink target stays within dest_path when resolved."""
    dest_path = os.path.abspath(dest_path)
    # For symlinks, resolve relative to dest_path
    if os.path.isabs(target):
        # Absolute link target: normalize and check if under dest_path
        resolved = os.path.abspath(target)
        return resolved.startswith(dest_path + os.sep) or resolved == dest_path
    else:
        # Relative link target: resolve relative to dest_path
        # Use a placeholder for the parent directory since we don't know exact location yet
        # We need to check all possible resolutions within dest_path
        # A relative target is safe if it doesn't escape when resolved from any point in dest_path
        # The worst case is resolving from dest_path itself (shallowest possible)
        resolved = os.path.normpath(os.path.join(dest_path, target))
        # Also check if intermediate .. components could escape
        # Split and check for escapes at each step
        parts = target.replace('\\', '/').split('/')
        current = dest_path
        for part in parts:
            if part == '..':
                current = os.path.dirname(current)
                if not current.startswith(dest_path) and current != dest_path:
                    return False
            elif part != '.' and part != '':
                current = os.path.join(current, part)
        # Final check: the normalized path must be under dest_path
        resolved = os.path.abspath(resolved)
        return resolved.startswith(dest_path + os.sep) or resolved == dest_path

def _get_link_target(member: tarfile.TarInfo) -> Optional[str]:
    """Get the link target from a tar member if it's a link."""
    if member.issym() or member.islnk():
        return member.linkname
    return None

def _validate_all_members(tar: tarfile.TarFile, dest_path: str) -> bool:
    """Validate all members before any extraction. Return True if all are safe."""
    dest_path = os.path.abspath(dest_path)
    
    for member in tar.getmembers():
        # Validate member name/path
        member_name = member.name
        
        # Reject absolute paths and paths with .. that escape
        normalized_name = _normalize_path(member_name)
        
        # Check for path traversal in member name
        if not _is_safe_path(normalized_name, dest_path):
            return False
        
        # Check link targets for symlinks and hardlinks
        link_target = _get_link_target(member)
        if link_target is not None:
            # For symlinks and hardlinks, validate the target
            if not _is_safe_link_target(link_target, dest_path):
                return False
            
            # For hardlinks, also verify the target file exists within the archive or will be created
            if member.islnk():
                # Hardlink target must be within dest_path and will exist after extraction
                # Additional check: hardlink target path must be safe
                target_normalized = _normalize_path(link_target)
                if os.path.isabs(link_target):
                    if not _is_safe_path(target_normalized, dest_path):
                        return False
                # else relative: already checked above
    
    return True

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive beneath dest_path.
    
    Returns True on complete success, False if validation or extraction fails.
    No archive member is written outside dest_path.
    """
    # Validate inputs
    if not os.path.isfile(tar_path):
        return False
    
    # Ensure dest_path exists and is a directory
    try:
        os.makedirs(dest_path, exist_ok=True)
    except OSError:
        return False
    
    dest_path = os.path.abspath(dest_path)
    
    try:
        # Open and validate all members before any extraction
        with tarfile.open(tar_path, 'r:*') as tar:
            # First pass: fully validate all members
            if not _validate_all_members(tar, dest_path):
                return False
            
            # Second pass: extract all members
            for member in tar.getmembers():
                # Double-check safety before extracting each member
                member_name = _normalize_path(member.name)
                if not _is_safe_path(member_name, dest_path):
                    return False
                
                link_target = _get_link_target(member)
                if link_target is not None:
                    if not _is_safe_link_target(link_target, dest_path):
                        return False
                
                # Extract the member
                tar.extract(member, path=dest_path, set_attrs=False)
                
    except (tarfile.TarError, OSError, IOError):
        return False
    
    return True
