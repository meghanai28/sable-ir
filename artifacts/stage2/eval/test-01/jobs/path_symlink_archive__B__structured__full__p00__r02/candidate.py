import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict path validation.
    
    Args:
        tar_path: Path to the tar archive.
        dest_path: Base directory where the archive should be extracted.
    
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    try:
        # Resolve the tar path to its absolute form
        tar_abs = os.path.abspath(tar_path)
        
        # Validate tar_path exists
        if not os.path.isfile(tar_abs):
            return False
        
        # Normalize dest_path to absolute form, resolving any .. segments
        dest_abs = os.path.abspath(dest_path)
        
        # Ensure the destination directory exists
        os.makedirs(os.path.dirname(dest_abs) if os.path.dirname(dest_abs) else '.', exist_ok=True)
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get the list of members to validate before extraction
            members = tar.getnames()
            
            for member in members:
                # Skip directories if they are not explicitly requested, 
                # but typically we want to extract all. We will extract all.
                # Resolve the member's potential destination path
                member_dir = os.path.dirname(member)
                member_file = os.path.basename(member)
                
                # Construct the full destination path for this member
                if member_dir:
                    dest_member = os.path.join(dest_abs, member_dir)
                else:
                    dest_member = dest_abs
                
                # Normalize the destination to check for escapes
                dest_member_abs = os.path.normpath(dest_member)
                
                # Security check: Ensure the member's destination is within dest_abs
                # We use os.path.commonpath to verify containment, handling the case where dest_abs is a prefix
                try:
                    common = os.path.commonpath([dest_abs, dest_member_abs])
                    if common != dest_abs:
                        return False
                except ValueError:
                    # This can happen if paths are on different drives (Windows) or invalid
                    return False
                
                # Additional check: Ensure no .. components remain in the relative path from dest_abs
                # by checking if the normalized path starts with dest_abs + os.sep or is exactly dest_abs
                if not (dest_member_abs == dest_abs or dest_member_abs.startswith(dest_abs + os.sep)):
                    return False
                
                # Extract the member
                tar.extract(member, dest_abs)
            
            return True
            
    except Exception:
        return False
