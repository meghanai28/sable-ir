import os
import tarfile
import stat
import sys

def _normalize_path(path: str) -> str:
    """Normalize path by resolving . and .. but without resolving symlinks."""
    return os.path.normpath(path)

def _is_under_base(target: str, base: str) -> bool:
    """Check if target is under base. Both must be absolute."""
    if not os.path.isabs(target) or not os.path.isabs(base):
        return False
    try:
        target_resolved = os.path.realpath(target)
        base_resolved = os.path.realpath(base)
        return target_resolved.startswith(base_resolved + os.sep) or target_resolved == base_resolved
    except (ValueError, OSError):
        return False

def _get_member_target(member: tarfile.TarFileMember) -> str:
    """Determine the filesystem target path for a member, resolving symlinks if possible."""
    if member.isdir:
        return member.name
    if member.issym():
        # Resolve symlink target
        try:
            link_target = member.linkname
            # Resolve .. and . in the link target relative to the member's directory
            member_dir = os.path.dirname(member.name)
            if member_dir:
                link_target = os.path.normpath(os.path.join(member_dir, link_target))
            else:
                link_target = os.path.normpath(link_target)
            return link_target
        except (OSError, ValueError):
            return member.name
    elif member.ishardlink():
        # Hard links point to another member in the archive or outside
        # We need to resolve the hardlink target
        try:
            link_target = member.linkname
            # If the link target is in the archive, resolve it relative to the member's directory
            if member.name in member.tarfile.getnames():
                member_dir = os.path.dirname(member.name)
                if member_dir:
                    link_target = os.path.normpath(os.path.join(member_dir, link_target))
                else:
                    link_target = os.path.normpath(link_target)
            return link_target
        except (OSError, ValueError):
            return member.name
    return member.name

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path.
    
    Args:
        tar_path: Path to the tar archive.
        dest_path: Destination directory for extraction.
    
    Returns:
        True if extraction completed successfully, False otherwise.
    """
    # Normalize and validate dest_path
    dest_path = _normalize_path(dest_path)
    
    # Check if dest_path escapes the root
    if not os.path.isabs(dest_path):
        return False
    
    try:
        if not os.path.exists(dest_path):
            os.makedirs(dest_path, exist_ok=True)
        
        # Validate dest_path doesn't escape root
        if not _is_under_path(dest_path, os.sep):
            return False
    except (OSError, ValueError):
        return False

    # Open the tar file
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get list of members
            members = tar.getmembers()
            
            # First pass: validate all members and their targets
            for member in members:
                target = _get_member_target(member)
                # Normalize the target to check for escapes
                norm_target = os.path.normpath(target)
                # Check if the target escapes the root or is outside dest_path
                if not _is_under_path(norm_target, dest_path):
                    return False
            
            # Second pass: extract members
            for member in members:
                try:
                    # Extract the member
                    tar.extract(member, dest_path)
                except (OSError, tarfile.TarError):
                    return False
            
            return True
            
    except (OSError, tarfile.TarError, ValueError):
        return False

def _is_under_path(path: str, base: str) -> bool:
    """
    Check if path is under base.
    Both must be absolute.
    """
    if not os.path.isabs(path) or not os.path.isabs(base):
        return False
    
    try:
        # Use realpath to handle any symlink escapes in the path itself
        # However, we want to prevent extraction to a path that escapes via ..
        # So we normalize without resolving symlinks for the check, but the spec says
        # "Normalize dest_path and raise an error if it escapes the root"
        # This implies we check the normalized path, not the resolved path of the path itself.
        # But for safety, we should check if the normalized path starts with base.
        if not path.startswith(base + os.sep) and path != base:
            return False
        return True
    except (ValueError, OSError):
        return False
