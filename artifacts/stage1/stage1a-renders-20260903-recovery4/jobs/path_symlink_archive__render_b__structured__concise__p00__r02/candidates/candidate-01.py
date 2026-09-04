import os
import tarfile
from typing import Optional


def _normalize_path(path: str) -> str:
    """Normalize a path without resolving symlinks."""
    return os.path.normpath(path)


def _is_path_within_bounds(resolved_path: str, bounds_path: str) -> bool:
    """Check if resolved_path is strictly within or equal to bounds_path."""
    try:
        # Use realpath to resolve any symlinks for the bounds check
        real_resolved = os.path.realpath(resolved_path)
        real_bounds = os.path.realpath(bounds_path)
        # Ensure the resolved path starts with the bounds path
        return real_resolved == real_bounds or real_resolved.startswith(real_bounds + os.sep)
    except (OSError, ValueError):
        return False


def _get_member_extract_path(member_name: str, dest_path: str) -> Optional[str]:
    """Get the normalized extraction path for a member, or None if invalid."""
    # Reject absolute paths in archive
    if os.path.isabs(member_name):
        return None
    
    # Normalize the member name
    normalized_name = _normalize_path(member_name)
    
    # Reject .. traversal
    if normalized_name.startswith('..' + os.sep) or normalized_name == '..' or '/../' in ('/' + normalized_name + '/'):
        # More thorough check: split and look for .. components after normalization
        parts = normalized_name.split(os.sep)
        for part in parts:
            if part == '..':
                return None
    
    # Compute full extraction path
    extract_path = os.path.join(dest_path, normalized_name)
    normalized_extract_path = _normalize_path(extract_path)
    
    # Ensure the normalized path is within dest_path
    if not _is_path_within_bounds(normalized_extract_path, dest_path):
        return None
    
    return normalized_extract_path


def _resolve_link_target(link_target: str, member_dir: str, dest_path: str) -> Optional[str]:
    """Resolve a link target and verify it's within dest_path. Returns resolved path or None."""
    # Reject absolute link targets
    if os.path.isabs(link_target):
        return None
    
    # Normalize the link target
    normalized_target = _normalize_path(link_target)
    
    # Reject .. traversal in the link target itself
    parts = normalized_target.split(os.sep)
    for part in parts:
        if part == '..':
            return None
    
    # Compute where the link would point to
    # For symlinks, resolve relative to the directory containing the link
    resolved_path = os.path.join(member_dir, normalized_target)
    normalized_resolved = _normalize_path(resolved_path)
    
    # Check bounds
    if not _is_path_within_bounds(normalized_resolved, dest_path):
        return None
    
    return normalized_resolved


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """Extract a tar archive beneath dest_path with strict path validation."""
    try:
        # Validate dest_path exists and is a directory
        if not os.path.isdir(dest_path):
            return False
        
        # Get absolute, real path of dest_path for consistent comparison
        dest_path = os.path.realpath(os.path.abspath(dest_path))
        
        # Open and validate the tar file
        try:
            tar = tarfile.open(tar_path, 'r:*')
        except (tarfile.TarError, OSError, IOError):
            return False
        
        try:
            # First pass: pre-validate all members
            members_to_extract = []
            
            for member in tar.getmembers():
                # Skip the root directory entry if present
                if member.name == '.' or member.name == './':
                    if member.isdir():
                        continue
                    return False
                
                # Get and validate extraction path for this member
                extract_path = _get_member_extract_path(member.name, dest_path)
                if extract_path is None:
                    return False
                
                # Validate link targets for symlinks and hard links
                if member.issym() or member.islnk():
                    if member.linkname is None:
                        return False
                    
                    # Get directory containing this member for relative link resolution
                    member_dir = os.path.dirname(extract_path)
                    
                    # For hard links, the target is another archive member
                    if member.islnk():
                        # Hard link target is relative to dest_path root
                        hardlink_target = _get_member_extract_path(member.linkname, dest_path)
                        if hardlink_target is None:
                            return False
                        # Also verify hard link target doesn't escape via realpath
                        if not _is_path_within_bounds(hardlink_target, dest_path):
                            return False
                    else:
                        # Symlink: resolve and validate target
                        resolved_target = _resolve_link_target(member.linkname, member_dir, dest_path)
                        if resolved_target is None:
                            return False
                
                # Store validated member info
                members_to_extract.append((member, extract_path))
            
            # Second pass: extract all members (only if validation passed)
            for member, extract_path in members_to_extract:
                # Extract to the parent directory of the final path, using safe name
                # We use extractfile and write manually for maximum control
                
                if member.isdir():
                    # Create directory
                    os.makedirs(extract_path, exist_ok=True)
                    # Apply mode if specified
                    if member.mode is not None:
                        try:
                            os.chmod(extract_path, member.mode)
                        except OSError:
                            pass
                
                elif member.isfile():
                    # Ensure parent directory exists
                    parent_dir = os.path.dirname(extract_path)
                    os.makedirs(parent_dir, exist_ok=True)
                    
                    # Extract file content
                    file_obj = tar.extractfile(member)
                    if file_obj is None:
                        return False
                    
                    try:
                        with open(extract_path, 'wb') as f:
                            while True:
                                chunk = file_obj.read(65536)
                                if not chunk:
                                    break
                                f.write(chunk)
                    finally:
                        file_obj.close()
                    
                    # Apply mode if specified
                    if member.mode is not None:
                        try:
                            os.chmod(extract_path, member.mode)
                        except OSError:
                            pass
                
                elif member.issym():
                    # Create symlink
                    parent_dir = os.path.dirname(extract_path)
                    os.makedirs(parent_dir, exist_ok=True)
                    
                    # Validate target again at extraction time
                    resolved_target = _resolve_link_target(member.linkname, parent_dir, dest_path)
                    if resolved_target is None:
                        return False
                    
                    # Check if symlink target would escape (defense in depth)
                    if os.path.exists(extract_path) or os.path.islink(extract_path):
                        os.remove(extract_path)
                    
                    os.symlink(member.linkname, extract_path)
                
                elif member.islnk():
                    # Create hard link
                    parent_dir = os.path.dirname(extract_path)
                    os.makedirs(parent_dir, exist_ok=True)
                    
                    # Validate hard link target
                    hardlink_target = _get_member_extract_path(member.linkname, dest_path)
                    if hardlink_target is None:
                        return False
                    
                    # Ensure target exists or will exist in archive
                    target_exists = False
                    for _, path in members_to_extract:
                        if path == hardlink_target:
                            target_exists = True
                            break
                    
                    # For hard links, target must exist or be earlier in archive
                    # We'll create in order, so check if already extracted or in list before us
                    if not target_exists and not os.path.exists(hardlink_target):
                        return False
                    
                    if os.path.exists(extract_path):
                        os.remove(extract_path)
                    
                    try:
                        os.link(hardlink_target, extract_path)
                    except OSError:
                        # Hard link may fail for various reasons (cross-device, etc.)
                        # Fall back to copy for safety, or return False
                        return False
                
                else:
                    # Unknown member type, reject
                    return False
            
            return True
            
        finally:
            tar.close()
            
    except (OSError, IOError, tarfile.TarError, ValueError):
        return False
