import os
import tarfile
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with security checks.
    
    - Rejects symbolic links and hard links entirely.
    - Resolves all archive member paths before extraction.
    - Ensures no member resolves outside dest_path.
    - Returns True only if extraction succeeds completely; False otherwise.
    """
    try:
        # Validate dest_path is within allowed scope (prevent absolute path bypass)
        if os.path.isabs(dest_path):
            dest_path = os.path.normpath(dest_path)
        
        # Normalize paths to prevent .. traversal
        dest_path = os.path.realpath(dest_path)
        
        # Ensure dest_path exists and is a directory
        if not os.path.isdir(dest_path):
            return False
        
        # Open the tar archive
        with tarfile.open(tar_path, 'r:*') as tar:
            # Check for symlinks or hardlinks in the archive
            for member in tar.getmembers():
                if member.issym() or member.islnk():
                    return False
            
            # Extract with safety checks
            for member in tar.getmembers():
                # Resolve the member's target path
                if member.isdir():
                    # For directories, use the member's name
                    member_path = os.path.join(dest_path, member.name)
                else:
                    # For files, resolve the path relative to dest_path
                    member_path = os.path.join(dest_path, member.name)
                
                # Normalize and resolve the path to check for .. traversal
                member_path = os.path.normpath(member_path)
                
                # Check if the resolved path is outside dest_path
                if not member_path.startswith(dest_path + os.sep) and member_path != dest_path:
                    return False
                
                # Extract the member
                tar.extract(member, dest_path)
            
            return True
            
    except Exception:
        return False
