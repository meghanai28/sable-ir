import os
import tarfile
import stat
import fnmatch

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination path with strict security validation.
    
    Returns True only if the entire archive is extracted successfully.
    Returns False if validation fails or extraction is incomplete.
    Raises an exception if the destination path is absolute or escapes the intended directory.
    """
    # Normalize the destination path to remove trailing slashes
    dest_path = dest_path.rstrip(os.sep)
    
    # Check if the destination path is absolute
    if os.path.isabs(dest_path):
        raise ValueError("Destination path must be relative.")
    
    # Resolve the destination directory (without the trailing separator)
    dest_dir = os.path.dirname(dest_path)
    if dest_dir == dest_path:
        raise ValueError("Destination path must be relative.")
    
    # Normalize the destination directory to remove .. and .
    normalized_dest_dir = os.path.normpath(dest_dir)
    
    # Validate that the destination directory is not a parent of itself (which would happen with ..)
    if not normalized_dest_dir.startswith(os.path.normpath(os.path.dirname(dest_dir))):
        raise ValueError("Destination path contains .. segments.")
    
    # Validate that the destination directory is not an ancestor of the current directory
    if not normalized_dest_dir.startswith(os.path.abspath(os.path.dirname(dest_dir))):
        raise ValueError("Destination path escapes the current directory.")
    
    # Create the destination directory if it doesn't exist
    os.makedirs(normalized_dest_dir, exist_ok=True)
    
    # Open the tar file
    tar = tarfile.open(tar_path, 'r:*')
    
    try:
        # Extract the archive members
        for member in tar.getmembers():
            # Validate the member's name
            if member.name.startswith('..') or '/' in member.name:
                raise ValueError(f"Invalid member name: {member.name}")
            
            # Resolve the member's name relative to the destination directory
            member_dest = os.path.normpath(os.path.join(normalized_dest_dir, member.name))
            
            # Check if the member's name escapes the destination directory
            if not member_dest.startswith(normalized_dest_dir + os.sep) and member_dest != normalized_dest_dir:
                raise ValueError(f"Member name escapes destination: {member.name}")
            
            # Check if the member's name is a symlink or hard link
            if member.issym() or member.islnk():
                # Resolve the link target
                link_target = member.linkname
                
                # Normalize the link target
                normalized_link_target = os.path.normpath(link_target)
                
                # Check if the link target escapes the destination directory
                if not normalized_link_target.startswith(os.sep) and not normalized_link_target.startswith(normalized_dest_dir + os.sep) and normalized_link_target != normalized_dest_dir:
                    raise ValueError(f"Symlink/hard link target escapes destination: {link_target}")
                
                # Check if the link target is a parent of the destination directory
                if normalized_link_target.startswith(os.path.normpath(os.path.dirname(normalized_dest_dir))):
                    raise ValueError(f"Symlink/hard link target escapes destination: {link_target}")
            
            # Check if the member's name is a symbolic or hard link
            if member.issym() or member.islnk():
                raise ValueError(f"Symlink or hard link not allowed: {member.name}")
            
            # Extract the member
            tar.extract(member, dest_dir)
    
    finally:
        tar.close()
    
    return True
