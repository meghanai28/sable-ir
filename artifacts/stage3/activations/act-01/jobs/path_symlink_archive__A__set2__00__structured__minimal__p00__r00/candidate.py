import os
import tarfile
import shutil

def _normalize_path(path: str) -> str:
    """Normalize a path to an absolute, canonical form without .. or ."""
    return os.path.realpath(path)

def _is_safe_subpath(member_name: str, dest_root: str) -> bool:
    """
    Check if a tar member's name, when resolved against dest_root,
    stays within dest_root. This handles cases where the member name
    does not contain '..' but resolves outside the root due to other path manipulations.
    """
    # Construct the full path where the member would be extracted
    # We use os.path.join to ensure proper handling of separators
    full_path = os.path.join(dest_root, member_name)
    
    # Normalize to handle any remaining .. or . and get the canonical path
    canonical_full = os.path.realpath(full_path)
    canonical_root = os.path.realpath(dest_root)
    
    # Ensure the canonical root ends with a separator for proper prefix checking
    if not canonical_root.endswith(os.sep):
        canonical_root += os.sep
    
    # Check if the member's resolved path starts with the root
    return canonical_full.startswith(canonical_root)

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to the directory specified by dest_path.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory where the archive should be extracted.
        
    Returns:
        True if extraction completes successfully without writing outside dest_path.
        False if any validation or extraction fails, or if any member would be written outside dest_path.
    """
    # Normalize the destination path immediately
    dest_root = _normalize_path(dest_path)
    
    # Normalize the source tar path
    tar_file = _normalize_path(tar_path)
    
    # Validate that the tar file exists
    if not os.path.isfile(tar_file):
        return False
    
    # Validate that the destination directory exists, create if not
    if not os.path.isdir(dest_root):
        try:
            os.makedirs(dest_root)
        except OSError:
            return False
    
    # Open the tar file for reading
    try:
        with tarfile.open(tar_file, 'r:*') as tar:
            # Iterate over all members in the archive
            for member in tar.getmembers():
                # Get the relative name of the member
                member_name = member.name
                
                # Skip empty names and device files if desired, but per spec we must guard against all
                if not member_name:
                    continue
                
                # Security check: ensure the member does not escape the destination root
                # We must check this even if the name doesn't contain '..'
                if not _is_safe_subpath(member_name, dest_root):
                    return False
                
                # Extract the member
                try:
                    tar.extract(member, dest_root)
                except (tarfile.TarError, OSError):
                    return False
                    
    except (tarfile.TarError, OSError):
        return False
    
    return True
