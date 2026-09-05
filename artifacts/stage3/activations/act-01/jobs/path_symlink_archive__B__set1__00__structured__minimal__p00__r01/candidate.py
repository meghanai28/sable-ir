import os
import tarfile
import stat
import sys

def _normalize_path(path: str) -> str:
    """Normalize a path to its absolute form, resolving . and .."""
    return os.path.normpath(os.path.abspath(path))

def _is_within_base(target: str, base: str) -> bool:
    """Check if target path is within base directory."""
    try:
        normalized_target = _normalize_path(target)
        normalized_base = _normalize_path(base)
        # Ensure base ends with a separator for proper prefix checking
        if not normalized_base.endswith(os.sep):
            normalized_base += os.sep
        return normalized_target.startswith(normalized_base)
    except (ValueError, OSError):
        return False

def _validate_tar_members(tar_path: str, dest_path: str) -> bool:
    """Validate all archive members to ensure none escape the destination."""
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            for member in tar.getmembers():
                # Resolve the member's name relative to the destination
                # The member's name might contain .. so we must check the resolved path
                member_path = os.path.normpath(os.path.join(dest_path, member.name))
                
                # Check if the member's name itself escapes
                # We need to resolve the full path as the archive might contain ..
                # But we also need to check link targets if present
                if not _is_within_base(member_path, dest_path):
                    return False
                
                # Check link targets
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    # Resolve the link target relative to the destination
                    # If it's an absolute path, it escapes immediately
                    if os.path.isabs(link_target):
                        return False
                    # Resolve relative to the destination
                    resolved_link = os.path.normpath(os.path.join(dest_path, link_target))
                    if not _is_within_base(resolved_link, dest_path):
                        return False
    except (tarfile.TarError, OSError, ValueError):
        return False
    
    return True

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive beneath dest_path.
    Returns True on complete success, False otherwise.
    """
    # Normalize the destination path immediately
    normalized_dest = _normalize_path(dest_path)
    
    # Validate that the tar file exists
    if not os.path.isfile(tar_path):
        return False
    
    # Validate all archive members before extraction
    if not _validate_tar_members(tar_path, normalized_dest):
        return False
    
    # Extract the archive
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Extract members one by one to maintain order and safety
            for member in tar:
                # Calculate the full path for this member
                member_path = os.path.normpath(os.path.join(normalized_dest, member.name))
                
                # Ensure the member path is still within the destination
                # (double-checking after joining)
                if not _is_within_base(member_path, normalized_dest):
                    return False
                
                # Extract the member
                tar.extract(member, path=normalized_dest)
                
                # Set permissions if specified by the archive
                if member.mode:
                    os.chmod(member_path, stat.S_IMODE(member.mode))
    except (tarfile.TarError, OSError, ValueError):
        return False
    
    return True
