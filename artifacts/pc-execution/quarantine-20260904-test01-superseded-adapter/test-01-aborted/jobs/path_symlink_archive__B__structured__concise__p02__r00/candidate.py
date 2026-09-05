import os
import tarfile
import shutil
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory with strict path validation.
    
    Args:
        tar_path: Path to the tar archive.
        dest_path: Destination directory for extraction.
        
    Returns:
        True if extraction completes successfully with all members inside dest_path.
        False if validation fails or extraction is interrupted.
    """
    try:
        # Normalize and validate dest_path immediately
        dest_path = os.path.normpath(dest_path)
        
        # Reject absolute paths
        if os.path.isabs(dest_path):
            raise ValueError("Destination path must be relative.")
        
        # Ensure dest_path is within root
        if not dest_path.startswith(os.sep) and not dest_path.startswith('.'):
            # If it's not absolute, check if it escapes root by looking at components
            parts = dest_path.split(os.sep)
            if any(part == '..' for part in parts):
                raise ValueError("Destination path contains '..' which escapes root.")
        
        # Create dest_path if it doesn't exist
        os.makedirs(dest_path, exist_ok=True)
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Validate all members before extraction
            for member in tar.getmembers():
                # Resolve the target path
                target_path = os.path.join(dest_path, member.name)
                
                # Normalize the target path
                normalized_target = os.path.normpath(target_path)
                
                # Check if the normalized target is within dest_path
                if not normalized_target.startswith(dest_path + os.sep) and normalized_target != dest_path:
                    raise ValueError(f"Member {member.name} would escape dest_path.")
                
                # Check for symbolic links and hard links
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    # Resolve the link target
                    if os.path.isabs(link_target):
                        resolved_link_target = os.path.normpath(link_target)
                    else:
                        resolved_link_target = os.path.normpath(os.path.join(dest_path, link_target))
                    
                    if not resolved_link_target.startswith(dest_path + os.sep) and resolved_link_target != dest_path:
                        raise ValueError(f"Symbolic/hard link target {link_target} would escape dest_path.")
                
                # Reject members with .. in their name that could escape
                if '..' in member.name.split(os.sep):
                    raise ValueError(f"Member {member.name} contains '..' which could escape dest_path.")
            
            # Extract the archive
            tar.extractall(path=dest_path)
            
            return True
    
    except Exception as e:
        # Ensure no partial extraction remains outside dest_path
        # Clean up any created files if an exception occurs
        if os.path.exists(dest_path):
            shutil.rmtree(dest_path)
        return False
