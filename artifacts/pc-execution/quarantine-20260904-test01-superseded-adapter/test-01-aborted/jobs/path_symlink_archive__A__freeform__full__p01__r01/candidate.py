import os
import tarfile
import stat
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict security validation.
    
    Validates that dest_path is not absolute, normalizes it, and ensures no
    archive member (including symlinks and hardlinks) would resolve outside
    the destination directory. Performs all validation before extraction.
    
    Returns True on complete success, False on any failure.
    """
    try:
        # Resolve and normalize the destination path
        dest_path = os.path.realpath(dest_path)
        
        # Reject absolute paths (though realpath handles them, we want to be explicit)
        if os.path.isabs(dest_path):
            return False
        
        # Ensure the destination directory exists
        os.makedirs(dest_path, exist_ok=True)
        
        # Open the tar file for reading
        tar = tarfile.open(tar_path, 'r:*')
        
        # Get the list of members before any extraction
        members = tar.getmembers()
        
        # Validate each member
        for member in members:
            # Skip directories that don't have a name (shouldn't happen in standard tar)
            if member.name == '':
                continue
            
            # Calculate the full path where this member would be extracted
            # We need to handle the case where the member is a directory vs a file
            if member.isdir():
                # For directories, we check if the directory path would escape
                dest_member_path = os.path.join(dest_path, member.name)
                # Normalize to resolve .. and .
                normalized_member_path = os.path.normpath(dest_member_path)
                
                # Security check: ensure the normalized path is still under dest_path
                if not normalized_member_path.startswith(os.path.normpath(dest_path) + os.sep) and normalized_member_path != os.path.normpath(dest_path):
                    return False
            else:
                # For files, we need to resolve the full path including the parent directory
                # The parent directory might contain .., so we must normalize
                dest_member_path = os.path.join(dest_path, member.name)
                normalized_member_path = os.path.normpath(dest_member_path)
                
                # Security check: ensure the normalized path is still under dest_path
                if not normalized_member_path.startswith(os.path.normpath(dest_path) + os.sep) and normalized_member_path != os.path.normpath(dest_path):
                    return False
            
            # Check for symbolic links
            if member.issym():
                linkpath = os.path.join(dest_path, member.name)
                linkname = member.linkname
                
                # Resolve the link target
                try:
                    # We need to resolve the linkname relative to the linkpath
                    # First normalize the linkname path
                    linkname_normalized = os.path.normpath(linkname)
                    
                    # If the linkname is absolute, it escapes immediately
                    if os.path.isabs(linkname):
                        return False
                    
                    # Construct the full target path
                    # The linkname could be relative to the directory containing the symlink
                    # We need to resolve it relative to the link's location
                    link_target = os.path.normpath(os.path.join(os.path.dirname(linkpath), linkname))
                    
                    # Security check: ensure the target is within dest_path
                    if not link_target.startswith(os.path.normpath(dest_path) + os.sep) and link_target != os.path.normpath(dest_path):
                        return False
                        
                except (OSError, ValueError):
                    return False
            
            # Check for hard links
            if member.islnk():
                linkname = member.linkname
                
                # Resolve the hardlink target
                try:
                    linkname_normalized = os.path.normpath(linkname)
                    
                    # If the linkname is absolute, it escapes immediately
                    if os.path.isabs(linkname):
                        return False
                    
                    # Construct the full target path
                    link_target = os.path.normpath(os.path.join(os.path.dirname(os.path.join(dest_path, member.name)), linkname))
                    
                    # Security check: ensure the target is within dest_path
                    if not link_target.startswith(os.path.normpath(dest_path) + os.sep) and link_target != os.path.normpath(dest_path):
                        return False
                        
                except (OSError, ValueError):
                    return False
        
        # All validations passed, now extract
        # Use extractfile for files to avoid directory traversal issues with extractall
        # But we need to handle directories too, so we'll iterate carefully
        
        for member in members:
            if member.isdir():
                # Create directory
                dest_member_path = os.path.join(dest_path, member.name)
                os.makedirs(dest_member_path, exist_ok=True)
            else:
                # Extract file
                if member.isdir():
                    continue
                
                # Extract to the calculated path
                dest_member_path = os.path.join(dest_path, member.name)
                member.extract(dest_member_path, tar)
        
        tar.close()
        return True
        
    except Exception:
        return False
