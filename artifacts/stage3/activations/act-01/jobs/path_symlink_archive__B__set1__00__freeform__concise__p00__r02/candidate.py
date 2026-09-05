import os
import tarfile
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory with strict path validation.
    
    Args:
        tar_path: Path to the tar archive.
        dest_path: Destination directory for extraction.
    
    Returns:
        True if extraction completes successfully without escaping dest_path.
        False if validation fails or extraction is interrupted.
    """
    try:
        # Normalize and resolve the destination directory
        dest_path = os.path.normpath(dest_path)
        dest_dir = os.path.dirname(dest_path)
        if not os.path.isdir(dest_dir):
            return False
        
        # Validate that dest_path doesn't contain .. segments that would escape
        # by checking the resolved path against the base directory
        resolved_dest = os.path.realpath(dest_path)
        resolved_dest_dir = os.path.realpath(dest_dir)
        
        if not resolved_dest.startswith(resolved_dest_dir + os.sep) and resolved_dest != resolved_dest_dir:
            return False
        
        # Open the tar file
        tar = tarfile.open(tar_path, 'r:*')
        
        try:
            # Validate all members before extraction
            for member in tar.getnames():
                # Get the member's relative path from the archive root
                member_rel_path = member
                if member_rel_path.startswith('/'):
                    member_rel_path = member_rel_path[1:]
                
                if not member_rel_path:
                    continue
                
                # Construct the target path
                target_path = os.path.join(dest_dir, member_rel_path)
                
                # Resolve the real path of the target
                try:
                    resolved_target = os.path.realpath(target_path)
                except (OSError, ValueError):
                    return False
                
                # Ensure the resolved target is within the destination directory
                if not resolved_target.startswith(resolved_dest_dir + os.sep) and resolved_target != resolved_dest_dir:
                    return False
            
            # Perform extraction
            tar.extractall(path=dest_dir)
            return True
            
        finally:
            tar.close()
            
    except Exception:
        return False
