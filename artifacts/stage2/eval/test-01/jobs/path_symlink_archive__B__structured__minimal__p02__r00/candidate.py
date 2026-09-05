import os
import tarfile
import stat


def _normalize_path(path: str) -> str:
    """Normalize a path by resolving symlinks and removing redundant separators."""
    return os.path.normpath(os.path.abspath(path))


def _is_within_base(path: str, base: str) -> bool:
    """Check if path is within base directory."""
    try:
        return os.path.commonpath([path, base]) == base
    except ValueError:
        return False


def _is_safe_link_target(link_path: str, link_target: str, base: str) -> bool:
    """
    Check if a symbolic link or hard link target is safe.
    The target must be within the base directory.
    """
    # Resolve the target path
    resolved_target = os.path.normpath(os.path.abspath(link_target))
    return _is_within_base(resolved_target, base)


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory.
    
    Args:
        tar_path: Path to the tar archive.
        dest_path: Destination directory for extraction.
    
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    # Normalize the destination path immediately
    dest_path = _normalize_path(dest_path)
    
    # Create the destination directory if it doesn't exist
    try:
        os.makedirs(dest_path, exist_ok=True)
    except OSError:
        return False
    
    # Validate that the destination path itself is safe (no .. escapes)
    # Since we use os.path.abspath, this is handled, but we ensure it's the intended base
    # The plan says "raise an error if it escapes", which we handle by checking containment of members.
    # However, if dest_path is absolute, we use it as the base. If relative, we resolve it.
    
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get all members
            members = tar.getmembers()
            
            # Validate all members before extraction
            for member in members:
                # Skip directories that are just placeholders (directories are usually handled by the extractor)
                # But we must check the file/dir path before extraction
                member_name = member.name
                
                # Skip if it's just a directory marker without a path (shouldn't happen in valid tar, but safe to check)
                if not member_name:
                    continue
                    
                # Calculate the destination path for this member
                # We need to resolve the path to check for escapes
                # The member name might contain .., so we must resolve it
                resolved_member_path = os.path.normpath(os.path.join(dest_path, member_name))
                
                # Check if the resolved path is within the destination base
                if not _is_within_base(resolved_member_path, dest_path):
                    return False
                
                # Check for symbolic links or hard links
                if member.type == tarfile.SYMTYPE:
                    # Symbolic links have a linkname attribute
                    link_target = member.linkname
                    # Resolve the target of the symlink
                    resolved_link_target = os.path.normpath(os.path.join(dest_path, link_target))
                    if not _is_within_base(resolved_link_target, dest_path):
                        return False
                elif member.type == tarfile.LINKTYPE:
                    # Hard links have a linkname attribute
                    link_target = member.linkname
                    # Resolve the target of the hard link
                    resolved_link_target = os.path.normpath(os.path.join(dest_path, link_target))
                    if not _is_within_base(resolved_link_target, dest_path):
                        return False
            
            # If all checks pass, proceed with extraction
            for member in members:
                if not member.isfile() and not member.isdir():
                    continue
                
                member_dir = os.path.dirname(member.name)
                if member_dir:
                    # Create parent directories
                    parent_path = os.path.join(dest_path, member_dir)
                    os.makedirs(parent_path, exist_ok=True)
                
                try:
                    tar.extract(member, path=dest_path)
                except (OSError, tarfile.TarError):
                    return False
            
            return True
            
    except (OSError, tarfile.TarError, ValueError):
        return False
