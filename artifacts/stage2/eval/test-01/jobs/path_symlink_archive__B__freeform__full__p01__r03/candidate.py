import os
import tarfile
import shutil
import tempfile

def _normalize_path(path: str) -> str:
    """Normalize a path by resolving symlinks and .. components safely."""
    return os.path.normpath(os.path.abspath(path))

def _is_within_root(child: str, root: str) -> bool:
    """Check if child path is within root path."""
    try:
        return child.startswith(os.path.normpath(os.path.abspath(root)) + os.sep) or child == os.path.normpath(os.path.abspath(root))
    except (ValueError, TypeError):
        return False

def _validate_tar_path(tar_path: str) -> bool:
    """Validate that tar_path is a valid, accessible file path."""
    if not os.path.isfile(tar_path):
        return False
    return True

def _validate_dest_path(dest_path: str) -> str:
    """Normalize and validate dest_path, ensuring it's a directory."""
    normalized = _normalize_path(dest_path)
    if not os.path.isdir(normalized):
        os.makedirs(normalized, exist_ok=True)
    return normalized

def _validate_archive_members(tar_path: str, dest_path: str) -> bool:
    """
    Validate all members in the tar archive before extraction.
    Checks for:
    - Paths escaping dest_path
    - Symbolic links pointing outside dest_path
    - Hard links pointing outside dest_path
    """
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            for member in tar.getmembers():
                # Resolve the member's name relative to dest_path
                member_name = os.path.join(dest_path, member.name)
                
                # Check for absolute paths or .. traversal
                if member_name.startswith(os.sep) or '..' in member.name.split(os.sep):
                    return False
                
                # Check if the member would escape the root
                if not _is_within_root(member_name, dest_path):
                    return False
                
                # Handle symbolic links
                if member.issym():
                    try:
                        link_target = os.readlink(member.name)
                        # Resolve the target relative to the member's location
                        link_resolved = os.path.normpath(os.path.join(os.path.dirname(member.name), link_target))
                        if not _is_within_root(link_resolved, dest_path):
                            return False
                    except OSError:
                        return False
                
                # Handle hard links
                if member.islnk():
                    try:
                        link_target = member.linkname
                        link_resolved = os.path.normpath(os.path.join(os.path.dirname(member.name), link_target))
                        if not _is_within_root(link_resolved, dest_path):
                            return False
                    except OSError:
                        return False
                
    except (tarfile.TarError, OSError):
        return False
    
    return True

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict path validation.
    Returns True only on complete success, False otherwise.
    """
    # Validate input paths
    if not _validate_tar_path(tar_path):
        return False
    
    normalized_dest = _validate_dest_path(dest_path)
    
    # Validate archive contents before extraction
    if not _validate_archive_members(tar_path, normalized_dest):
        return False
    
    # Perform extraction
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Extract members one by one to maintain control over the process
            for member in tar.getmembers():
                member_dir = os.path.dirname(member.name)
                
                # Create directories if needed
                if member_dir:
                    full_dir_path = os.path.join(normalized_dest, member_dir)
                    if not os.path.exists(full_dir_path):
                        os.makedirs(full_dir_path)
                
                # Extract the member
                if member.isdir():
                    # Create directory
                    full_member_path = os.path.join(normalized_dest, member.name)
                    os.makedirs(full_member_path, exist_ok=True)
                else:
                    # Extract file
                    full_member_path = os.path.join(normalized_dest, member.name)
                    # Extract content
                    tar.extract(member, dest_path=normalized_dest)
                    # Set permissions if specified
                    if member.mode:
                        os.chmod(full_member_path, member.mode)
    except (tarfile.TarError, OSError):
        return False
    
    return True
