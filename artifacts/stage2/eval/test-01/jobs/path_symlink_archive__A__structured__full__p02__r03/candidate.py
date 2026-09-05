import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with security validation.
    
    Returns True on complete success, False if validation or extraction fails.
    No archive members are written outside dest_path.
    """
    # Resolve and normalize the destination path
    try:
        resolved_dest = os.path.realpath(dest_path)
    except (ValueError, OSError):
        return False
    
    # Validate tar_path exists and is a file
    try:
        if not os.path.isfile(tar_path):
            return False
    except (OSError, ValueError):
        return False
    
    # Normalize tar_path to resolve symlinks for path checking
    tar_real_path = os.path.realpath(tar_path)
    
    # Open the tar file
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get list of members before extraction
            members = tar.getmembers()
            
            for member in members:
                # Skip directories (they are handled by extracting files)
                if member.isdir():
                    continue
                
                # Security checks
                # 1. Check for symbolic links or hard links
                if member.issym() or member.ishardlink():
                    return False
                
                # 2. Check for relative paths that might escape
                # 3. Check for absolute paths
                if member.name.startswith('/'):
                    return False
                
                # 4. Check if the member's name contains '..'
                if '..' in member.name:
                    return False
                
                # 5. Calculate the target path and verify it's within dest_path
                target_path = os.path.join(resolved_dest, member.name)
                # Normalize to resolve any remaining .. or .
                normalized_target = os.path.normpath(target_path)
                
                # Ensure the normalized target is still within the resolved dest
                # We need to check if normalized_target starts with resolved_dest + os.sep
                # or equals resolved_dest (for root extraction)
                if not (normalized_target == resolved_dest or normalized_target.startswith(resolved_dest + os.sep)):
                    return False
            
            # If all checks pass, extract the archive
            # Use extractall to extract all members at once
            tar.extractall(path=resolved_dest)
            
    except (tarfile.TarError, OSError, ValueError):
        return False
    
    return True
