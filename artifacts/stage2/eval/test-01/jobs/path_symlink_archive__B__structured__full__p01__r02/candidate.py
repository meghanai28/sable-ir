import os
import tarfile
import stat

def _normalize_path(path: str) -> str:
    """Normalize a path to remove redundant separators and resolve . and .. components."""
    return os.path.normpath(path)

def _is_within_root(target: str, root: str) -> bool:
    """Check if target is within root directory."""
    try:
        target = os.path.realpath(target)
        root = os.path.realpath(root)
        return target.startswith(root + os.sep) or target == root
    except (ValueError, OSError):
        return False

def _validate_member(member_name: str, dest_path: str) -> bool:
    """Validate a tar member to ensure it stays within dest_path and doesn't follow unsafe links."""
    try:
        if member_name.startswith('/'):
            member_name = member_name[1:]
        
        # Resolve the destination path for this member
        dest_path = _normalize_path(dest_path)
        member_dest = os.path.join(dest_path, member_name)
        
        # Check for directory traversal
        if '..' in member_name.split(os.sep):
            return False
        
        # Calculate the absolute path for the member
        abs_member_dest = os.path.abspath(member_dest)
        
        # Ensure the destination is within the allowed root
        if not _is_within_root(abs_member_dest, dest_path):
            return False
        
        # Check if it's a symbolic link or hard link
        if member_name.endswith('/'):
            # It's a directory, check if it contains any symlinks or hard links
            try:
                stat_info = os.stat(abs_member_dest)
                if stat_info.st_mode & stat.S_ISLNK:
                    return False
                if stat_info.st_mode & stat.S_ISLNK:
                    return False
            except (OSError, ValueError):
                return False
        else:
            # It's a file, check if it's a symlink
            try:
                stat_info = os.stat(abs_member_dest)
                if stat_info.st_mode & stat.S_ISLNK:
                    return False
            except (OSError, ValueError):
                return False
        
        return True
    except (ValueError, OSError):
        return False

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """Extract a tar archive beneath dest_path. Returns True on complete success, False otherwise."""
    try:
        # Normalize and validate the destination path
        dest_path = _normalize_path(dest_path)
        
        # Validate the tar file exists
        if not os.path.isfile(tar_path):
            return False
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get the list of members
            members = tar.getnames()
            
            # Validate all members before extraction
            for member_name in members:
                if not _validate_member(member_name, dest_path):
                    return False
            
            # Extract the archive
            tar.extractall(dest_path)
            
            return True
    
    except (tarfile.TarError, OSError, ValueError):
        return False
