import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory with strict security validation.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory for extraction.
        
    Returns:
        True if extraction completes successfully, False otherwise.
        No archive members are written outside dest_path on failure.
    """
    # 1. Order: Check components of dest_path before opening or reading the tar archive
    if not os.path.isdir(dest_path):
        return False
    
    # Normalize dest_path to absolute and resolve symlinks
    try:
        dest_path = os.path.abspath(dest_path)
    except (OSError, ValueError):
        return False
    
    # GUARD: Reject absolute dest_path that starts with root or has ..
    if dest_path.startswith(os.sep) or dest_path.startswith('/'):
        return False
    
    # Normalize dest_path to remove trailing slashes and resolve . and ..
    dest_path = os.path.normpath(dest_path)
    
    # GUARD: Ensure dest_path does not escape the root directory
    if not dest_path.startswith(os.sep) and dest_path != '.':
        return False
    
    # 2. Order: Walk each member of the archive, resolve link targets, validate before extraction
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Create destination directory if it doesn't exist (but ensure it's under our control)
            # We need to create parent directories but stop if we go outside dest_path
            parent_dirs = []
            for part in dest_path.split(os.sep):
                if part and part != '.' and part != '':
                    parent_dirs.append(part)
            
            # Build the path to check
            check_path = dest_path
            for part in parent_dirs:
                check_path = os.path.join(check_path, part)
                if not os.path.exists(check_path):
                    try:
                        os.makedirs(check_path)
                    except (OSError, ValueError):
                        return False
            
            # Validate the final dest_path is safe
            if not dest_path.startswith(os.sep) and dest_path != '.':
                return False
                
            # Extract members
            for member in tar.getmembers():
                # GUARD: Resolve link targets and validate they remain inside dest_path
                # Check hard links and symbolic links
                if member.issym():
                    # Symbolic link
                    link_target = member.linkname
                    # Resolve the link target relative to the member's directory
                    member_dir = os.path.dirname(member.name)
                    resolved_link = os.path.normpath(os.path.join(member_dir, link_target))
                    
                    # GUARD: Check if resolved link escapes dest_path
                    if not resolved_link.startswith(dest_path) or resolved_link == dest_path:
                        return False
                    
                    # Create the directory if needed
                    if member.isdir():
                        os.makedirs(member.name, exist_ok=True)
                    elif member.name != dest_path:
                        os.makedirs(os.path.dirname(member.name), exist_ok=True)
                        
                    # Create the symlink
                    try:
                        os.symlink(link_target, member.name)
                    except (OSError, ValueError):
                        return False
                        
                elif member.islnk():
                    # Hard link
                    link_target = member.linkname
                    # Resolve the link target relative to the member's directory
                    member_dir = os.path.dirname(member.name)
                    resolved_link = os.path.normpath(os.path.join(member_dir, link_target))
                    
                    # GUARD: Check if resolved link escapes dest_path
                    if not resolved_link.startswith(dest_path) or resolved_link == dest_path:
                        return False
                    
                    # Create the directory if needed
                    if member.isdir():
                        os.makedirs(member.name, exist_ok=True)
                    elif member.name != dest_path:
                        os.makedirs(os.path.dirname(member.name), exist_ok=True)
                        
                    # Create the hard link
                    try:
                        os.link(link_target, member.name)
                    except (OSError, ValueError):
                        return False
                        
                elif member.isfile() or member.isdir():
                    # Regular file or directory
                    # Create the directory if needed
                    if member.isdir():
                        os.makedirs(member.name, exist_ok=True)
                    elif member.name != dest_path:
                        os.makedirs(os.path.dirname(member.name), exist_ok=True)
                        
                    # Extract the file
                    try:
                        tar.extract(member, dest_path)
                    except (OSError, ValueError):
                        return False
                        
    except (tarfile.TarError, OSError, IOError):
        return False
    
    return True
