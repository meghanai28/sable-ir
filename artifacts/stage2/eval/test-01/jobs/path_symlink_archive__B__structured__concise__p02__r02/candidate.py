import os
import tarfile
import stat

def _normalize_path(path: str) -> str:
    """Resolve a path to its absolute, normalized form without following symlinks."""
    return os.path.realpath(path)

def _is_under_dest(archive_path: str, dest_path: str) -> bool:
    """Check if archive_path is under dest_path."""
    return archive_path.startswith(dest_path)

def _is_member_safe(member: tarfile.TarInfo, dest_path: str) -> bool:
    """Check if a tar member would be extracted safely under dest_path."""
    # Resolve the target path for the member
    if member.isdir():
        target = dest_path + os.sep + member.name
    else:
        target = dest_path + os.sep + member.name
    
    # Normalize the target to ensure it's absolute and resolved
    normalized_target = os.path.normpath(target)
    
    # Ensure the normalized target is within dest_path
    if not normalized_target.startswith(dest_path + os.sep):
        return False
    
    # If it's a symlink, check if the link target is safe
    if member.issym() or member.islnk():
        link_target = member.linkname
        # Resolve the link target relative to the member's location
        if member.isdir():
            resolved_link = os.path.normpath(os.path.join(dest_path, member.name, link_target))
        else:
            resolved_link = os.path.normpath(os.path.join(dest_path, member.name, link_target))
        
        if not resolved_link.startswith(dest_path + os.sep):
            return False
    
    return True

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """Extract a tar archive beneath dest_path and return True on complete success."""
    try:
        # Normalize the destination path
        dest_path = _normalize_path(dest_path)
        
        # Check if the destination path is absolute
        if not os.path.isabs(dest_path):
            dest_path = os.path.abspath(dest_path)
        
        # Normalize the tar path
        tar_path = _normalize_path(tar_path)
        
        # Validate that the tar file exists
        if not os.path.isfile(tar_path):
            return False
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Walk through the archive members and validate them
            for member in tar.getnames():
                # Skip the root directory if it's not the top-level directory
                if member == '/':
                    continue
                
                # Check if the member would be extracted safely
                if not _is_member_safe(tar.getmember(member), dest_path):
                    return False
            
            # If all members are safe, extract the archive
            tar.extractall(dest_path)
        
        return True
    
    except Exception:
        return False
