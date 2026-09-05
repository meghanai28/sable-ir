import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict path validation.
    
    Args:
        tar_path: Path to the tar archive.
        dest_path: Destination directory for extraction.
        
    Returns:
        True if extraction completes successfully without writing outside dest_path.
        False if any validation or extraction fails.
    """
    try:
        # Normalize dest_path to absolute and ensure it's within root
        dest_path = os.path.normpath(os.path.abspath(dest_path))
        
        # Reject absolute paths that start with root directly or contain ..
        if dest_path.startswith(os.sep) or dest_path.startswith('\\'):
            return False
            
        # Check for .. components in the normalized path
        if '..' in dest_path:
            return False
            
        # Create dest_path if it doesn't exist
        if not os.path.exists(dest_path):
            os.makedirs(dest_path)
            
        # Open the archive and validate members before extraction
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get list of all members first
            members = tar.getmembers()
            
            # Validate each member's path
            for member in members:
                # Resolve the full path
                full_path = os.path.normpath(os.path.join(dest_path, member.name))
                
                # Check for .. in the resolved path
                if '..' in full_path:
                    return False
                    
                # Check if the resolved path is outside dest_path
                # We need to ensure the resolved path starts with dest_path
                if not full_path.startswith(dest_path + os.sep) and full_path != dest_path:
                    return False
                    
                # Handle symbolic links
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    resolved_link = os.path.normpath(os.path.join(dest_path, link_target))
                    
                    # Check for .. in the link target
                    if '..' in resolved_link:
                        return False
                        
                    # Check if the resolved link target is outside dest_path
                    if not resolved_link.startswith(dest_path + os.sep) and resolved_link != dest_path:
                        return False
                        
            # Now perform the extraction
            for member in members:
                if member.isdir():
                    os.makedirs(os.path.join(dest_path, member.name))
                elif member.issym() or member.islnk():
                    link_target = member.linkname
                    os.symlink(link_target, os.path.join(dest_path, member.name))
                else:
                    # Extract the file
                    member.copy(dest_path)
                    
            return True
            
    except Exception:
        return False
