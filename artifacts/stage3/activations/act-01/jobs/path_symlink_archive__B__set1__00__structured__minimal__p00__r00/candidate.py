import os
import tarfile
import tempfile
import shutil


def _normalize_path(path: str) -> str:
    """Normalize a path to an absolute path without resolving symlinks."""
    return os.path.normpath(path)


def _is_within_destination(base: str, target: str) -> bool:
    """Check if target path is within base directory."""
    base = _normalize_path(base)
    target = _normalize_path(target)
    return target.startswith(base + os.sep) or target == base


def _validate_tar_members(tar_path: str, dest_path: str) -> list:
    """Validate tar members to ensure none escape the destination directory.
    
    Returns:
        List of valid member names or raises ValueError if unsafe.
    """
    with tarfile.open(tar_path, 'r:*') as tar:
        for member in tar.getmembers():
            # Resolve the member's path relative to dest_path
            # We need to check the final destination of the member
            dest_member = os.path.normpath(os.path.join(dest_path, member.name))
            
            # Check if the member path itself escapes
            if not _is_within_destination(dest_path, dest_member):
                raise ValueError(f"Unsafe member path: {member.name} -> {dest_member}")
            
            # Check link targets if the member is a link
            if member.issym() or member.islnk():
                link_target = member.linkname
                # Normalize the link target relative to the member's location
                if os.path.isabs(link_target):
                    # Absolute link targets are dangerous
                    normalized_link = _normalize_path(link_target)
                    if not _is_within_destination(dest_path, normalized_link):
                        raise ValueError(f"Unsafe link target: {link_target} -> {normalized_link}")
                else:
                    # Relative link targets need to be resolved relative to the member's directory
                    member_dir = os.path.dirname(dest_member)
                    normalized_link = os.path.normpath(os.path.join(member_dir, link_target))
                    if not _is_within_destination(dest_path, normalized_link):
                        raise ValueError(f"Unsafe link target: {link_target} -> {normalized_link}")
    
    return []


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """Extract a tar archive to the specified destination path.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory for extraction.
        
    Returns:
        True if extraction completed successfully, False otherwise.
    """
    # Normalize the destination path
    dest_path = _normalize_path(dest_path)
    
    # Validate that the tar_path exists
    if not os.path.isfile(tar_path):
        return False
    
    # Validate all members before extraction
    try:
        _validate_tar_members(tar_path, dest_path)
    except ValueError as e:
        return False
    
    # Create a temporary directory for extraction
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Extract to temporary directory
            with tarfile.open(tar_path, 'r:*') as tar:
                tar.extractall(temp_dir)
            
            # Move the extracted contents to the destination
            # We need to handle the case where dest_path might be a file (though unlikely for extraction)
            if os.path.isfile(dest_path):
                return False
            
            # Calculate the source directory to move
            source_dir = os.path.join(temp_dir, os.listdir(temp_dir)[0]) if os.listdir(temp_dir) else temp_dir
            
            # Ensure the destination directory exists
            os.makedirs(dest_path, exist_ok=True)
            
            # Move the contents
            if os.path.isdir(source_dir):
                shutil.move(source_dir, dest_path)
            
            return True
            
        except Exception:
            return False
