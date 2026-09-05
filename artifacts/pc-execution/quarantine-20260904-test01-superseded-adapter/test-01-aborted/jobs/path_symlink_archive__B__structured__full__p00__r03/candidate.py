import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict path traversal protection.
    
    Args:
        tar_path: Path to the tar archive.
        dest_path: Destination directory for extraction.
        
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    try:
        # Normalize dest_path to absolute and remove trailing slashes
        dest_path = os.path.normpath(dest_path)
        
        # Guard: Reject absolute paths that start with root
        if dest_path.startswith(os.sep) or dest_path.startswith('\\'):
            return False
            
        # Guard: Ensure dest_path is not a symlink to something outside root
        # We'll check this during the walk, but first ensure we don't extract to a symlink
        if os.path.islink(dest_path):
            return False
            
        # Create dest_path directory if it doesn't exist
        os.makedirs(dest_path, exist_ok=True)
        
        # Open the archive and extract members
        with tarfile.open(tar_path, 'r:*') as tar:
            # Guard: Walk each member before extracting
            for member in tar.getmembers():
                # Resolve the member's path relative to dest_path
                member_path = os.path.normpath(os.path.join(dest_path, member.name))
                
                # Guard: Check for path traversal attempts
                if not member_path.startswith(dest_path):
                    return False
                
                # Guard: Check if the member is a symlink or hardlink
                if member.issym() or member.islnk():
                    # Resolve the link target
                    link_target = member.linkname
                    
                    # Guard: Ensure link target is within dest_path
                    # Resolve relative to the parent directory of the link
                    parent_dir = os.path.dirname(member_path)
                    resolved_link = os.path.normpath(os.path.join(parent_dir, link_target))
                    
                    if not resolved_link.startswith(dest_path):
                        return False
                    
                    # For symlinks, we need to be careful about the resolved path
                    # The link itself is safe if the target is safe
                    # But we also need to ensure the link target doesn't point to something outside
                    # Check if the resolved link is within dest_path
                    if not resolved_link.startswith(dest_path):
                        return False
                
                # Guard: Check if the member is a hardlink
                if member.islnk():
                    # Hardlink target is specified in the linkname field
                    # The target should be relative to the same directory as the link
                    link_target = member.linkname
                    parent_dir = os.path.dirname(member_path)
                    resolved_hardlink = os.path.normpath(os.path.join(parent_dir, link_target))
                    
                    if not resolved_hardlink.startswith(dest_path):
                        return False
                
                # Extract the member
                tar.extract(member, dest_path)
                
        return True
        
    except Exception:
        return False
