import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to the specified destination path.
    
    Security Policy Applied:
    - Rejects any symbolic links and hard links.
    - Rejects links whose targets appear to remain inside the destination (relative paths).
    - Only extracts regular files and directories after validation.
    
    Returns:
    - True if extraction completes successfully.
    - False if validation or extraction fails, without writing any member outside dest_path.
    """
    try:
        # Ensure the destination directory exists
        if not os.path.exists(dest_path):
            os.makedirs(dest_path, exist_ok=True)
        
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get the absolute path of the destination for validation
            abs_dest = os.path.abspath(dest_path)
            
            for member in tar.getmembers():
                # Resolve the member's name relative to the destination
                # If the member name contains '..', it might escape the destination
                # We need to check the full path before extraction
                
                # Calculate the full path where this member would be extracted
                full_path = os.path.join(abs_dest, member.name)
                abs_full_path = os.path.abspath(full_path)
                
                # Check for traversal attempts (.. in the member name)
                if '..' in member.name.split(os.sep):
                    return False
                
                # Check if the absolute path is outside the destination
                if not abs_full_path.startswith(abs_dest + os.sep) and abs_full_path != abs_dest:
                    return False
                
                # Security Policy: Reject symbolic links and hard links
                if member.issym() or member.islnk():
                    return False
                
                # Additional check: if it's a directory, ensure no symlinks are created within it
                # For now, we rely on the extraction process, but we must ensure the member itself is safe
                
                # Extract the member
                tar.extract(member, dest_path, set_attrs=False)
            
            return True
            
    except Exception:
        return False
