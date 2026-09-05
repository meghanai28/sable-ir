import os
import tarfile
import stat

def _validate_dest(dest_path: str) -> None:
    """Normalize dest_path and raise if it escapes the resolved destination."""
    # Resolve to absolute path, handling relative paths by current dir
    resolved = os.path.realpath(dest_path)
    
    # Check for .. traversal in the normalized path
    # We compare the normalized path against the resolved base
    # If the normalized path starts with the resolved base + separator, it's safe
    # However, we must also ensure the normalized path doesn't contain .. that would go above the base
    # A robust check: ensure the normalized path is within the resolved directory
    if not resolved.endswith(os.sep):
        resolved += os.sep
    
    # The resolved path should be a prefix of the normalized path
    if not (normalized_path := os.path.realpath(dest_path)).startswith(resolved):
        # If normalized_path starts with resolved, it's safe. Otherwise, it escapes.
        # Note: os.path.realpath resolves symlinks. We need to be careful not to resolve too much if the user
        # intends to use a symlinked directory as the base, but the spec says "raise if it escapes".
        # The safest approach for security is to ensure the extracted path is a subdirectory of the provided dest_path.
        # We check if the normalized path is strictly within the resolved destination directory.
        if not normalized_path.startswith(resolved) or (normalized_path == resolved and os.path.basename(normalized_path) != ''):
            raise ValueError(f"dest_path escapes the allowed directory: {dest_path}")

def _validate_archive_members(tar_path: str) -> None:
    """Walk the archive's member list and raise if any member is a symbolic link or hard link."""
    with tarfile.open(tar_path, 'r:*') as tar:
        for member in tar.getmembers():
            # Check for symbolic links
            if member.issym():
                raise ValueError(f"Symbolic link found in archive: {member.name}")
            # Check for hard links
            if member.islnk():
                raise ValueError(f"Hard link found in archive: {member.name}")
            # Additional check: if the member name contains .., it's unsafe regardless of type
            if '..' in member.name:
                raise ValueError(f"Unsafe path component '..' found in archive member: {member.name}")

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """Extract a tar archive beneath dest_path. Returns True on complete success, False otherwise."""
    try:
        # Validate destination path first
        _validate_dest(dest_path)
        
        # Validate archive members before extraction
        _validate_archive_members(tar_path)
        
        # Resolve the destination directory
        dest_dir = os.path.dirname(os.path.realpath(dest_path))
        
        with tarfile.open(tar_path, 'r:*') as tar:
            # Extract members, filtering out symlinks and hardlinks, and only extracting regular files/dirs
            # We use filter to ensure only safe members are processed
            for member in tar.getmembers():
                # Skip symlinks and hardlinks (already caught in validation, but good for extraction filter)
                if member.issym() or member.islnk():
                    continue
                
                # Construct the target path
                target_path = os.path.join(dest_dir, member.name)
                
                # Ensure the target path is still within the safe directory
                # Resolve the target path to catch any .. in the member name that might have slipped through
                resolved_target = os.path.realpath(target_path)
                if not resolved_target.startswith(dest_dir + os.sep):
                    # This should have been caught by _validate_archive_members, but we check again for safety
                    raise ValueError(f"Extracted path escapes destination: {member.name}")
                
                # Extract the member
                # extractfile extracts the member, but we need to ensure we don't follow symlinks
                # Since we filtered symlinks/hardlinks above, we can safely extract regular files and dirs
                tar.extract(member, dest_dir, filter='data')
                
        return True
        
    except Exception:
        return False
