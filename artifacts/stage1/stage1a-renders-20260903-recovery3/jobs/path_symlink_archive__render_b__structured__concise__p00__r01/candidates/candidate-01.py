import os
import tarfile
from typing import Optional


def _normalize_path(path: str) -> Optional[str]:
    """Normalize a path and return None if it contains suspicious components."""
    # Reject absolute paths
    if os.path.isabs(path):
        return None
    
    # Normalize the path
    normalized = os.path.normpath(path)
    
    # Reject paths that escape via .. or start with / after normalization
    if normalized.startswith('..') or normalized.startswith('/'):
        return None
    
    # Reject empty paths and paths with .. components that didn't get caught
    parts = normalized.split(os.sep)
    if any(p == '..' for p in parts):
        return None
    
    if normalized == '.' or normalized == '':
        return None
    
    return normalized


def _is_within_dest(full_path: str, dest_real: str) -> bool:
    """Check if full_path is strictly within dest_real."""
    try:
        real_path = os.path.realpath(full_path)
        # Ensure it's within dest and not equal to dest itself (strict containment)
        return real_path.startswith(dest_real + os.sep) or real_path == dest_real
    except (OSError, ValueError):
        return False


def _validate_member(member: tarfile.TarInfo, dest_path: str, dest_real: str) -> bool:
    """Validate a single tar member's extraction path and link targets."""
    # Validate member name/path
    normalized_name = _normalize_path(member.name)
    if normalized_name is None:
        return False
    
    # Calculate full extraction path
    full_member_path = os.path.join(dest_path, normalized_name)
    member_real = os.path.realpath(full_member_path)
    
    # Must be within dest_path
    if not member_real.startswith(dest_real + os.sep) and member_real != dest_real:
        return False
    
    # Validate link targets for symlinks and hard links
    if member.issym() or member.islnk():
        if member.issym():
            # Symlink: validate the link target
            link_target = member.linkname
            
            # Reject absolute symlink targets
            if os.path.isabs(link_target):
                return False
            
            # Normalize the link target
            normalized_target = os.path.normpath(link_target)
            if normalized_target.startswith('..') or normalized_target.startswith('/'):
                return False
            
            parts = normalized_target.split(os.sep)
            if any(p == '..' for p in parts):
                return False
            
            # Resolve the symlink target relative to the member's directory
            member_dir = os.path.dirname(full_member_path)
            resolved_target = os.path.normpath(os.path.join(member_dir, link_target))
            
            # Must resolve within dest_path
            try:
                real_target = os.path.realpath(resolved_target)
                # For symlinks, check if the resolved path would be within dest
                # Use the parent directory's realpath to resolve relative symlinks
                if not real_target.startswith(dest_real + os.sep) and real_target != dest_real:
                    return False
            except (OSError, ValueError):
                return False
        
        elif member.islnk():
            # Hard link: validate the link target (another archive member)
            link_target = member.linkname
            
            # Reject absolute hard link targets
            if os.path.isabs(link_target):
                return False
            
            normalized_target = _normalize_path(link_target)
            if normalized_target is None:
                return False
            
            full_target_path = os.path.join(dest_path, normalized_target)
            try:
                real_target = os.path.realpath(full_target_path)
                if not real_target.startswith(dest_real + os.sep) and real_target != dest_real:
                    return False
            except (OSError, ValueError):
                return False
    
    return True


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """Extract a tar archive beneath dest_path and return True on complete success."""
    # Validate dest_path exists and is a directory
    if not os.path.isdir(dest_path):
        return False
    
    # Get real path of dest_path to prevent traversal via symlinks in dest_path itself
    try:
        dest_real = os.path.realpath(dest_path)
    except (OSError, ValueError):
        return False
    
    # Ensure dest_real ends with separator for proper prefix checking
    if not dest_real.endswith(os.sep):
        dest_real = dest_real + os.sep
    
    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
            
            # Pre-validate all members before any extraction
            for member in members:
                if not _validate_member(member, dest_path, dest_real.rstrip(os.sep)):
                    return False
            
            # All members validated, now extract
            for member in members:
                # Re-validate and extract each member individually
                normalized_name = _normalize_path(member.name)
                if normalized_name is None:
                    return False
                
                full_member_path = os.path.join(dest_path, normalized_name)
                
                # Double-check the path is still safe (TOCTOU protection)
                try:
                    member_real = os.path.realpath(full_member_path)
                    dest_real_clean = dest_real.rstrip(os.sep)
                    if not member_real.startswith(dest_real_clean + os.sep) and member_real != dest_real_clean:
                        return False
                except (OSError, ValueError):
                    return False
                
                # Extract the member
                try:
                    tf.extract(member, dest_path)
                except (OSError, tarfile.TarError, IOError):
                    return False
            
            return True
            
    except (OSError, tarfile.TarError, IOError):
        return False
