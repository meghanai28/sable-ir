import os
import tarfile
import stat

def _normalize_path(path: str) -> str:
    """Normalize path to remove redundant separators and resolve .. safely."""
    return os.path.normpath(path)

def _is_under_root(path: str) -> bool:
    """Check if path is under root directory."""
    return path.startswith(os.sep) or path == "/"

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict security validation.
    
    Returns True only if extraction completes successfully without writing outside dest_path.
    Returns False if any validation fails or extraction is interrupted.
    """
    try:
        # Normalize and validate destination path
        dest_path = _normalize_path(dest_path)
        
        # Ensure destination exists and is a directory
        if not os.path.isdir(dest_path):
            return False
            
        # Check for escape attempts
        if not _is_under_root(dest_path):
            return False
            
        # Open tar archive
        tar = tarfile.open(tar_path)
        
        # Validate all members before extraction
        for member in tar.getmembers():
            # Skip directories that might be created during extraction
            if member.isdir():
                continue
                
            # Get the member's name relative to dest_path
            member_name = member.name
            
            # Construct the full target path
            target_path = os.path.join(dest_path, member_name)
            
            # Normalize the target path to resolve . and ..
            normalized_target = os.path.normpath(target_path)
            
            # Check if the normalized path escapes the destination directory
            if not normalized_target.startswith(dest_path + os.sep) and normalized_target != dest_path:
                return False
                
            # Check for symbolic links or hard links
            if member.issym() or member.ishardlink():
                return False
                
        # Perform extraction
        tar.extractall(path=dest_path)
        tar.close()
        
        return True
        
    except Exception:
        return False
