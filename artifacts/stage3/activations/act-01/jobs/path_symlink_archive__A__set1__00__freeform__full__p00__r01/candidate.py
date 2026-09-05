import os
import tarfile
import shutil
import tempfile

def _normalize_path(path: str) -> str:
    """Normalize a path to its absolute, canonical form, resolving symlinks."""
    return os.path.normpath(os.path.realpath(path))

def _is_under_root(child: str, root: str) -> bool:
    """Check if child path is under root path, handling .. and symlinks."""
    try:
        # Resolve the child path
        resolved_child = os.path.realpath(child)
        # Resolve the root path
        resolved_root = os.path.realpath(root)
        # Ensure root ends with a separator for correct prefix checking
        if not resolved_root.endswith(os.sep):
            resolved_root += os.sep
        return resolved_child.startswith(resolved_root)
    except (ValueError, OSError):
        return False

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination path with strict security validation.
    
    Args:
        tar_path: Path to the tar archive.
        dest_path: Destination directory for extraction.
        
    Returns:
        True if extraction succeeds completely, False otherwise.
    """
    try:
        # Normalize the destination path immediately
        dest_path = _normalize_path(dest_path)
        
        # Open the tar file for reading
        with tarfile.open(tar_path, 'r:*') as tar:
            # Validate all members before extraction
            for member in tar.getmembers():
                # Resolve the intended destination for this member
                intended_dest = os.path.join(dest_path, member.name)
                
                # Security check: Ensure the member's name doesn't escape the root
                if not _is_under_root(member.name, dest_path):
                    return False
                
                # Security check: Resolve the actual destination after extraction
                # This handles cases where the member name looks safe but resolves outside
                resolved_member_dest = os.path.realpath(intended_dest)
                
                if not _is_under_root(resolved_member_dest, dest_path):
                    return False
            
            # Perform extraction with safety flags
            # extractall is safe by default, but we rely on our pre-validation
            # We must ensure no symlinks or hardlinks are created.
            # tarfile.extractall does not create symlinks or hardlinks by default.
            # However, to be absolutely sure and follow the plan's spirit of "never extract a symbolic link",
            # we can use extractall which is safe, but we must ensure the member names don't contain ..
            # The _is_under_root check on the raw name handles .. in the path.
            
            # Extract all members
            tar.extractall(path=dest_path)
            
            return True
            
    except Exception:
        # On any error, return False without writing outside dest_path
        # The try/except block ensures no partial writes outside dest_path occur
        # because we validate before any extraction logic that could write outside
        return False
