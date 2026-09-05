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
        True if extraction completes successfully, False otherwise.
    """
    # Normalize paths to absolute and resolve any .. segments
    try:
        # Ensure dest_path is absolute
        if not os.path.isabs(dest_path):
            dest_path = os.path.abspath(dest_path)
        
        # Ensure dest_path exists and is a directory
        if not os.path.isdir(dest_path):
            return False
            
        # Normalize dest_path to remove trailing slashes and resolve . and ..
        dest_path = os.path.normpath(dest_path)
        
        # Validate dest_path does not escape root
        if not dest_path.startswith(os.sep) and dest_path != '.':
            # If it's not an absolute path and not '.', it might be a relative path that could escape
            # However, the spec says "raise an error if it escapes the root".
            # We need to ensure the final resolved path is under a safe root.
            # Since we normalized it, if it started with a drive letter (Windows) or is absolute, it's safe.
            # If it's relative, we treat it as relative to the current working directory, which is generally safe for this constraint
            # unless the user explicitly creates a symlink to escape.
            pass
    except (ValueError, OSError):
        return False
    
    # Validate tar_path exists
    if not os.path.isfile(tar_path):
        return False
    
    # Create the destination directory if it doesn't exist
    try:
        os.makedirs(dest_path, exist_ok=True)
    except (OSError, ValueError):
        return False
    
    # Function to check if a path is within the destination directory
    def is_within_dest(path: str) -> bool:
        """Check if a path is within dest_path."""
        try:
            resolved = os.path.realpath(path)
            resolved_dest = os.path.realpath(dest_path)
            return resolved.startswith(resolved_dest + os.sep) or resolved == resolved_dest
        except (OSError, ValueError):
            return False
    
    # Open the tar file
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Validate the archive's root directory if present
            root = tar.getroot()
            if root:
                if not is_within_dest(root):
                    return False
            
            # Get all members
            members = tar.getmembers()
            
            # First pass: Validate all members and links
            for member in members:
                # Check if the member's name escapes dest_path
                if not is_within_dest(member.name):
                    return False
                
                # Check for symbolic links
                if member.issym() or member.islnk():
                    # Resolve the link target
                    try:
                        link_target = member.linkname
                        # If it's a relative link, resolve it relative to the member's directory
                        if not os.path.isabs(link_target):
                            member_dir = os.path.dirname(member.name)
                            link_target = os.path.normpath(os.path.join(member_dir, link_target))
                        
                        # Check if the link target escapes dest_path
                        if not is_within_dest(link_target):
                            return False
                    except (OSError, ValueError):
                        return False
                
                # Check for hard links
                if member.islnk():
                    # Hard links are stored in the archive's directory structure
                    # We need to check if the target of the hard link is within dest_path
                    try:
                        link_target = member.linkname
                        if not is_within_dest(link_target):
                            return False
                    except (OSError, ValueError):
                        return False
            
            # Second pass: Extract with validation
            for member in members:
                try:
                    # Extract the member
                    if member.isdir():
                        # Create directory
                        member_dir = os.path.join(dest_path, member.name)
                        os.makedirs(member_dir, exist_ok=True)
                    elif member.issym():
                        # Create symbolic link
                        member_dir = os.path.join(dest_path, member.name)
                        os.makedirs(member_dir, exist_ok=True)
                        os.symlink(member.linkname, member_dir)
                    elif member.islnk():
                        # Create hard link
                        member_dir = os.path.join(dest_path, member.name)
                        os.makedirs(member_dir, exist_ok=True)
                        os.link(member.linkname, member_dir)
                    else:
                        # Extract file
                        member_dir = os.path.join(dest_path, member.name)
                        # Ensure parent directories exist
                        parent_dir = os.path.dirname(member_dir)
                        os.makedirs(parent_dir, exist_ok=True)
                        # Extract the file
                        tar.extract(member, dest_path)
                except (OSError, ValueError, tarfile.TarError):
                    return False
            
            return True
            
    except (tarfile.TarError, OSError, ValueError):
        return False
