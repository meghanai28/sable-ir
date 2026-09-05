import os
import tarfile
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Safely extract a tar archive to a destination directory.
    
    Validates that dest_path is within the root directory.
    Validates that no archive member would escape dest_path.
    Never follows symbolic links that point outside the root or escape dest_path.
    
    Returns True on complete success, False on any failure.
    """
    # Normalize paths to absolute and resolve to canonical form where possible
    # We must resolve the root of dest_path to ensure it's under /
    try:
        root_dir = os.path.realpath(os.path.abspath('/'))
    except (OSError, ValueError):
        return False
    
    # Normalize dest_path to absolute
    dest_path = os.path.abspath(dest_path)
    
    # Resolve dest_path to canonical form if possible, but handle errors gracefully
    try:
        dest_path_real = os.path.realpath(dest_path)
    except (OSError, ValueError):
        # If we can't resolve dest_path, treat it as potentially unsafe
        return False
    
    # Check if dest_path escapes the root
    if not dest_path_real.startswith(root_dir + os.sep) and dest_path_real != root_dir:
        return False
    
    # Ensure dest_path exists and is a directory
    try:
        os.makedirs(dest_path, exist_ok=True)
    except OSError:
        return False
    
    # Open the tar archive
    try:
        tar = tarfile.open(tar_path, 'r:*')
    except (tarfile.TarError, OSError, ValueError):
        return False
    
    try:
        for member in tar.getmembers():
            # Skip directories to avoid writing outside dest_path during extraction
            if member.isdir():
                continue
            
            # Check if member name is absolute or contains ..
            # We need to resolve the full path of the member relative to dest_path
            member_name = member.name
            dest_path_full = os.path.join(dest_path, member_name)
            
            # Resolve the destination
            try:
                dest_path_resolved = os.path.realpath(dest_path_full)
            except (OSError, ValueError):
                # If we can't resolve, it might be a symlink or invalid path
                return False
            
            # Check if the resolved path escapes dest_path
            if not dest_path_resolved.startswith(dest_path_real + os.sep) and dest_path_resolved != dest_path_real:
                return False
            
            # Additional check for absolute paths in member names
            if member_name.startswith('/') or '..' in member_name.split(os.sep):
                # Re-evaluate based on the plan's specific requirement about absolute names
                # The plan says: "walk each archive member whose name is absolute or contains .."
                # We already checked .. above, but let's be strict about absolute paths
                if member_name.startswith('/'):
                    return False
            
            # Check for symlinks
            if member.issym():
                # Resolve the symlink target
                try:
                    link_target = member.linkname
                    # Resolve the link target relative to the member's location
                    # This is tricky because tarfile doesn't always give us the full path
                    # We need to resolve the link target relative to the member's directory
                    member_dir = os.path.dirname(member_name)
                    link_target_full = os.path.join(member_dir, link_target)
                    
                    try:
                        link_target_resolved = os.path.realpath(link_target_full)
                    except (OSError, ValueError):
                        return False
                    
                    # Check if the resolved link target escapes dest_path
                    if not link_target_resolved.startswith(dest_path_real + os.sep) and link_target_resolved != dest_path_real:
                        return False
                except Exception:
                    return False
            
            # Extract the member
            try:
                tar.extract(member, dest_path)
            except (tarfile.TarError, OSError):
                return False
    
    finally:
        tar.close()
    
    return True
