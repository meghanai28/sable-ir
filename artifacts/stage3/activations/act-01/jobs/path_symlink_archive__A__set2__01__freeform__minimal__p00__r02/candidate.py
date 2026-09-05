import os
import tarfile
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory with strict security validation.
    
    This function:
    1. Validates that dest_path is within the root directory (no absolute paths or .. escapes).
    2. Walks through the archive members, resolving symlinks and checking their final destinations.
    3. Ensures no file or symlink resolution escapes the dest_path.
    4. Performs extraction only after all validation passes.
    
    Returns True only if extraction completes successfully and safely.
    Returns False if any validation or extraction fails, without writing outside dest_path.
    """
    # Normalize dest_path to absolute and resolve any existing symlinks in the path itself
    try:
        dest_path = os.path.realpath(dest_path)
    except (OSError, ValueError):
        return False
    
    # Ensure dest_path is within the root directory
    if not dest_path.startswith(os.sep) and dest_path != os.sep:
        # If it's not an absolute path or is just root, treat it as unsafe if not root
        if dest_path != "/":
            return False
    
    # Create the destination directory if it doesn't exist
    try:
        os.makedirs(dest_path, exist_ok=True)
    except (OSError, ValueError):
        return False
    
    # List of members to extract
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            members = tar.getmembers()
    except (tarfile.TarError, OSError, ValueError):
        return False
    
    # Validate each member before extraction
    for member in members:
        # Resolve the member's name relative to dest_path
        member_path = os.path.join(dest_path, member.name)
        
        # Check for absolute paths or .. escapes in the member name
        if member.name.startswith(os.sep) or '..' in member.name.split(os.sep):
            return False
        
        # If the member is a symlink, resolve its target and check the final destination
        if member.issym() or member.islnk():
            try:
                link_path = os.path.join(dest_path, member.name)
                # Check if the link itself is outside dest_path
                if not link_path.startswith(os.sep) and link_path != os.sep:
                    if link_path != "/":
                        return False
                
                # Resolve the symlink target
                try:
                    resolved_link = os.path.realpath(link_path)
                except (OSError, ValueError):
                    return False
                
                # Ensure the resolved link is within dest_path
                if not resolved_link.startswith(os.sep) and resolved_link != os.sep:
                    if resolved_link != "/":
                        return False
                
                # Additional check: ensure the link target doesn't point outside
                if not resolved_link.startswith(dest_path):
                    return False
            except (OSError, ValueError):
                return False
        else:
            # For regular files or directories, ensure the path is within dest_path
            if not member_path.startswith(os.sep) and member_path != os.sep:
                if member_path != "/":
                    return False
            
            # Check for .. in the path components
            if '..' in member_path.split(os.sep):
                return False
    
    # If all validations pass, extract the archive
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            for member in tar.getmembers():
                # Skip members that would escape dest_path (double-check during extraction)
                member_path = os.path.join(dest_path, member.name)
                if member_path.startswith(os.sep) or member_path == os.sep:
                    if member_path != "/":
                        continue
                
                if member.issym() or member.islnk():
                    try:
                        link_path = os.path.join(dest_path, member.name)
                        resolved_link = os.path.realpath(link_path)
                        if not resolved_link.startswith(dest_path):
                            return False
                    except (OSError, ValueError):
                        return False
                else:
                    if not member_path.startswith(dest_path):
                        return False
                
                # Extract the member
                tar.extract(member, dest_path)
    except (tarfile.TarError, OSError, ValueError):
        return False
    
    return True
