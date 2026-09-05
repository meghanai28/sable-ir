import os
import tarfile
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict path containment validation.
    
    Args:
        tar_path: Path to the tar archive.
        dest_path: Destination directory for extraction.
        
    Returns:
        True if extraction completes successfully with all members inside dest_path.
        False if validation fails, extraction fails, or any member would escape dest_path.
    """
    # Normalize dest_path to an absolute path, resolving .. and .
    try:
        dest_path = os.path.realpath(dest_path)
    except (ValueError, OSError):
        return False
    
    # Ensure dest_path is a directory
    if not os.path.isdir(dest_path):
        return False
    
    # Create the destination directory if it doesn't exist
    try:
        os.makedirs(dest_path, exist_ok=True)
    except (OSError, ValueError):
        return False
    
    # Validate that dest_path is within the root filesystem (no escape)
    # realpath should have resolved .., but we double-check against root
    try:
        root = os.path.realpath('/')
        if not dest_path.startswith(root) and dest_path != root:
            return False
    except (ValueError, OSError):
        return False
    
    # Open the tar file
    try:
        tar = tarfile.open(tar_path, 'r:*')
    except (tarfile.TarError, OSError, ValueError):
        return False
    
    try:
        for member in tar.getmembers():
            # Skip directories (dir=0) as they are not extracted by default
            if member.isdir():
                continue
            
            # Check if the member name itself escapes the destination
            # by resolving the path relative to dest_path
            member_path = os.path.join(dest_path, member.name)
            
            # Resolve the member path to check for .. traversal
            try:
                resolved_member_path = os.path.realpath(member_path)
            except (ValueError, OSError):
                return False
            
            # Ensure the resolved path is within dest_path
            if not resolved_member_path.startswith(dest_path) or resolved_member_path == dest_path:
                return False
            
            # Check symbolic links and hard links
            if member.issym() or member.islnk():
                # Resolve the link target
                link_target = member.linkname
                link_path = os.path.join(dest_path, member.name)
                
                # For symlinks, we need to resolve the target relative to the link location
                # and ensure the final resolved location is within dest_path
                try:
                    resolved_link_target = os.path.realpath(link_path + os.sep + link_target)
                except (ValueError, OSError):
                    return False
                
                # The resolved link target must be within dest_path
                if not resolved_link_target.startswith(dest_path) or resolved_link_target == dest_path:
                    return False
            
            # Check hard links
            if member.islnk():
                # Hard links are stored in the archive metadata
                # The target is given in the linkname field
                link_target = member.linkname
                link_path = os.path.join(dest_path, member.name)
                
                # Resolve the target path
                try:
                    resolved_link_target = os.path.realpath(link_path + os.sep + link_target)
                except (ValueError, OSError):
                    return False
                
                # Ensure the resolved target is within dest_path
                if not resolved_link_target.startswith(dest_path) or resolved_link_target == dest_path:
                    return False
            
            # Extract the member
            try:
                tar.extract(member, dest_path, set_attrs=True)
            except (tarfile.TarError, OSError, ValueError):
                return False
    
    finally:
        tar.close()
    
    return True
