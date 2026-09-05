import os
import tarfile
import tempfile

def _normalize_path(path: str, base: str) -> str:
    """Resolve a path relative to base and return the absolute normalized path."""
    if not os.path.isabs(path):
        path = os.path.join(base, path)
    return os.path.normpath(path)

def _is_within_dest(target: str, dest: str) -> bool:
    """Check if the target path is within the destination directory."""
    try:
        target = os.path.normpath(target)
        dest = os.path.normpath(dest)
        # Ensure dest ends with a separator for correct prefix checking
        if not dest.endswith(os.sep):
            dest += os.sep
        return target.startswith(dest)
    except (ValueError, TypeError):
        return False

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive beneath dest_path.
    
    Returns:
        True if extraction completes successfully.
        False if validation fails or extraction is interrupted, without writing outside dest_path.
    """
    try:
        # Normalize the destination path immediately to prevent escape via relative paths
        dest_path = os.path.normpath(dest_path)
        
        # Validate that dest_path is absolute or can be resolved safely
        if not os.path.isabs(dest_path):
            # If caller passes a relative dest, we treat it as relative to current dir,
            # but we must ensure the final resolved path doesn't escape.
            # However, per the plan, we normalize and check.
            pass
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get list of all members
            members = tar.getnames()
            
            # Validate each member before extraction
            for member in members:
                # Resolve the member's target relative to dest_path
                # We need to check if the member itself or any link target escapes
                # The member name might contain '..'
                member_path = _normalize_path(member, dest_path)
                
                # Check if the member path escapes the destination
                if not _is_within_dest(member_path, dest_path):
                    return False
                
                # Check link targets
                if member.islnk() or member.islysym():
                    # For symbolic links, we must check the target
                    # tarfile.getmember() returns the link target
                    link_target = member.linkname
                    link_target_path = _normalize_path(link_target, dest_path)
                    if not _is_within_dest(link_target_path, dest_path):
                        return False
            
            # If all checks pass, perform extraction
            # We use extractall but we need to ensure it doesn't write outside
            # Since we validated all members, extractall should be safe regarding path traversal
            # However, we must ensure the extraction directory exists
            if not os.path.exists(dest_path):
                os.makedirs(dest_path, exist_ok=True)
            
            # Extract the archive
            tar.extractall(path=dest_path)
            
        return True
        
    except Exception:
        return False
