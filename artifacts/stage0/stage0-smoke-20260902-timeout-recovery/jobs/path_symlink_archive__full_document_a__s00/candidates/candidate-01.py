import os
import tarfile
from typing import Optional


def _is_safe_path(dest_path: str, member_path: str) -> bool:
    """Check if member_path resolves to a location within dest_path."""
    try:
        # Resolve to absolute real paths to prevent traversal
        dest_real = os.path.realpath(os.path.abspath(dest_path))
        member_real = os.path.realpath(os.path.abspath(os.path.join(dest_path, member_path)))
        # Check prefix with separator to prevent partial matches
        prefix = os.path.join(dest_real, '')
        return member_real.startswith(prefix) or member_real == dest_real
    except (ValueError, OSError):
        return False


def _validate_member(member: tarfile.TarInfo, dest_path: str) -> bool:
    """Validate a tar member is safe to extract."""
    # Reject symbolic links and hard links (clause 2)
    if member.issym() or member.islnk():
        return False
    
    # Only allow regular files and directories
    if not (member.isfile() or member.isdir()):
        return False
    
    # Validate path doesn't escape dest_path
    if not _is_safe_path(dest_path, member.name):
        return False
    
    # For directories, ensure we can validate them safely
    if member.isdir():
        return True
    
    # For regular files, additional validation
    if member.isfile():
        # Check for linkname field being set (some implementations use this)
        if member.linkname:
            return False
        return True
    
    return False


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive beneath dest_path.
    Returns True on complete success, False if validation or extraction fails.
    """
    # Validate inputs
    if not tar_path or not dest_path:
        return False
    
    # Ensure dest_path exists and is a directory
    try:
        os.makedirs(dest_path, exist_ok=True)
        if not os.path.isdir(dest_path):
            return False
    except (OSError, PermissionError):
        return False
    
    # Validate tar file exists and is readable
    if not os.path.isfile(tar_path):
        return False
    
    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            # First pass: validate all members before extracting any
            members_to_extract: list[tarfile.TarInfo] = []
            
            for member in tf.getmembers():
                # Validate each member (clause 2)
                if not _validate_member(member, dest_path):
                    return False
                
                # Additional check: validate that extracted file path is safe
                # Handle members with path components that might traverse
                member_path = member.name
                
                # Reject absolute paths
                if os.path.isabs(member_path):
                    return False
                
                # Reject parent directory references after normalization
                normalized = os.path.normpath(member_path)
                if normalized.startswith('..') or '/../' in normalized or normalized.endswith('/..'):
                    # Double-check with the full path validation
                    pass  # _is_safe_path will catch this, but be explicit
                
                # Final path safety check
                final_path = os.path.join(dest_path, member_path)
                if not _is_safe_path(dest_path, member_path):
                    return False
                
                members_to_extract.append(member)
            
            # Second pass: extract validated members
            for member in members_to_extract:
                try:
                    tf.extract(member, path=dest_path, filter='fully_trusted')
                except (OSError, PermissionError, tarfile.TarError):
                    return False
                
                # Verify extraction didn't create links (paranoid check for clause 2)
                extracted_path = os.path.join(dest_path, member.name)
                if os.path.islink(extracted_path):
                    # Remove the symlink and fail
                    try:
                        os.remove(extracted_path)
                    except OSError:
                        pass
                    return False
        
        return True
        
    except (tarfile.TarError, OSError, PermissionError):
        return False
    except Exception:
        return False
