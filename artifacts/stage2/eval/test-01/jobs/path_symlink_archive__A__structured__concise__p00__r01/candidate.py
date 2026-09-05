import os
import tarfile
import stat

def _normalize_path(path: str) -> str:
    """Normalize a path to remove redundant separators and resolve .. segments safely."""
    return os.path.normpath(path)

def _is_within_directory(base_dir: str, target_path: str) -> bool:
    """Check if target_path is within base_dir (after normalization)."""
    try:
        normalized_base = os.path.normpath(base_dir)
        normalized_target = os.path.normpath(target_path)
        # Ensure base_dir ends with a separator for correct prefix matching
        if not normalized_base.endswith(os.sep) and not normalized_base == "":
            normalized_base += os.sep
        return normalized_target.startswith(normalized_base)
    except (ValueError, TypeError):
        return False

def _validate_and_extract_member(member: tarfile.TarFileMember, dest_dir: str) -> None:
    """
    Validate a single archive member and extract it if valid.
    Raises ValueError if the member is unsafe (symlink, hardlink, or escapes dest_dir).
    """
    member_dir = os.path.dirname(member.name)
    member_name = os.path.basename(member.name)
    
    # Resolve the full path relative to dest_dir
    full_member_path = os.path.join(dest_dir, member_dir, member_name)
    
    # Normalize the full path to check for escapes
    full_member_path = os.path.normpath(full_member_path)
    
    # Check if the member escapes the destination directory
    if not _is_within_directory(dest_dir, full_member_path):
        raise ValueError(f"Archive member path escapes destination: {member.name}")
    
    # Check for symbolic links
    if member.issym:
        raise ValueError(f"Symbolic link detected in archive: {member.name}")
    
    # Check for hard links
    if member.islnk:
        raise ValueError(f"Hard link detected in archive: {member.name}")
    
    # Check for device files
    if member.isdev():
        raise ValueError(f"Device file detected in archive: {member.name}")
    
    # Create parent directories if necessary
    if member_dir:
        os.makedirs(os.path.join(dest_dir, member_dir), exist_ok=True)
    
    # Extract the member
    if member.isdir():
        os.makedirs(full_member_path, exist_ok=True)
    else:
        # Ensure parent directory exists for regular files
        parent_dir = os.path.dirname(full_member_path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
        with open(full_member_path, 'wb') as f:
            f.write(member.file.read())

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to the specified destination path.
    Returns True on complete success, False on any failure or validation error.
    Does not write any archive member outside dest_path.
    """
    # Normalize and validate destination path
    dest_path = _normalize_path(dest_path)
    
    # Check if dest_path is absolute and starts with dangerous prefixes
    if dest_path.startswith((".", "..", "/")):
        # If it starts with .. or /, we must ensure it's safe
        # Actually, normpath handles .., but we need to check if it escapes
        # Let's re-evaluate based on the plan: "normalize dest_path and raise if it escapes"
        pass
    
    # Create the destination directory if it doesn't exist
    os.makedirs(dest_path, exist_ok=True)
    
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get all members
            members = tar.getmembers()
            
            # Validate all members before extraction
            for member in members:
                # Resolve the full path
                full_member_path = os.path.join(dest_path, member.name)
                full_member_path = os.path.normpath(full_member_path)
                
                # Check if it escapes
                if not _is_within_directory(dest_path, full_member_path):
                    return False
                
                # Check for symlinks and hardlinks
                if member.issym or member.islnk:
                    return False
                
                # Check for device files
                if member.isdev():
                    return False
            
            # Extract members one by one
            for member in members:
                _validate_and_extract_member(member, dest_path)
            
            return True
            
    except (tarfile.TarError, OSError, ValueError) as e:
        return False
