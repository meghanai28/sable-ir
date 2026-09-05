import os
import tarfile
import tempfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict path validation.
    
    This function validates that:
    1. dest_path does not escape the root directory.
    2. All archive members, including symbolic and hard link targets, resolve to paths within dest_path.
    3. The archive's destination directory itself does not escape the root.
    
    It returns True only if extraction completes successfully without violating safety constraints.
    Returns False if validation fails or extraction fails, without writing any archive member outside dest_path.
    """
    # Normalize dest_path to an absolute path if necessary
    dest_path = os.path.normpath(dest_path)
    
    # Check if dest_path escapes the root
    if not dest_path.startswith(os.sep) and dest_path != '.':
        # If it's not absolute, we need to resolve it relative to cwd, but for safety,
        # we treat non-absolute paths as potentially unsafe if they could be manipulated.
        # However, the spec says "normalize dest_path and raise an error if it escapes the root".
        # We'll resolve it to an absolute path first.
        try:
            dest_path = os.path.abspath(dest_path)
        except (ValueError, OSError):
            return False
    
    # Ensure dest_path is absolute and doesn't escape root
    if not dest_path.startswith(os.sep) and dest_path != '.':
        # If it's still not absolute, it might be a relative path.
        # We need to check if it escapes root.
        # But the safest approach is to make it absolute.
        pass
    
    # Final check: ensure dest_path is absolute and doesn't start with '..' or escape root
    if dest_path.startswith(('.', '..')):
        return False
    
    # Create a temporary directory for extraction to ensure we don't write outside dest_path
    # We will extract to a temp dir, validate paths, then move if valid.
    # Actually, the spec says "without writing any archive member outside dest_path".
    # So we should extract to dest_path directly but validate before writing.
    
    # Let's create the dest_path directory if it doesn't exist
    try:
        os.makedirs(dest_path, exist_ok=True)
    except (OSError, ValueError):
        return False
    
    # Validate dest_path doesn't escape root
    if not dest_path.startswith(os.sep) and dest_path != '.':
        # If it's not absolute, we assume it's relative to cwd.
        # But we need to ensure it doesn't escape root.
        # We'll resolve it to absolute and check.
        pass
    
    # Resolve dest_path to absolute
    try:
        dest_path = os.path.abspath(dest_path)
    except (ValueError, OSError):
        return False
    
    # Check if dest_path escapes root
    if not dest_path.startswith(os.sep) and dest_path != '.':
        return False
    
    # Check for .. in dest_path
    if '..' in dest_path:
        return False
    
    # Open the tar file
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Validate archive members
            for member in tar.getmembers():
                # Get the full path of the member
                member_path = os.path.join(dest_path, member.name)
                
                # Normalize the path to handle ..
                member_path = os.path.normpath(member_path)
                
                # Check if the member path escapes root
                if not member_path.startswith(os.sep) and member_path != '.':
                    return False
                
                # Check for .. in the normalized path
                if '..' in member_path:
                    return False
                
                # Check if the member path is within dest_path
                if not member_path.startswith(dest_path + os.sep) and member_path != dest_path:
                    return False
                
                # Handle symbolic links and hard links
                if member.issym() or member.islnk():
                    # Get the link target
                    link_target = member.linkname
                    
                    # Resolve the link target
                    link_target_path = os.path.join(dest_path, link_target)
                    link_target_path = os.path.normpath(link_target_path)
                    
                    # Check if the link target escapes root
                    if not link_target_path.startswith(os.sep) and link_target_path != '.':
                        return False
                    
                    # Check for .. in the link target
                    if '..' in link_target_path:
                        return False
                    
                    # Check if the link target is within dest_path
                    if not link_target_path.startswith(dest_path + os.sep) and link_target_path != dest_path:
                        return False
                
                # Handle hard links
                if member.islnk():
                    # Hard links don't have a target, but we need to ensure the target is within dest_path
                    # The target is the same as the link name in the archive, but we need to check the destination
                    pass
                
                # Check if the member name is safe
                if not member.name.startswith(os.sep) and member.name != '.':
                    return False
                
                if '..' in member.name:
                    return False
                
                if not member.name.startswith(dest_path + os.sep) and member.name != dest_path:
                    return False
            
            # Now extract the archive
            for member in tar:
                member_path = os.path.join(dest_path, member.name)
                
                # Normalize the path
                member_path = os.path.normpath(member_path)
                
                # Check if the member path escapes root
                if not member_path.startswith(os.sep) and member_path != '.':
                    return False
                
                # Check for .. in the normalized path
                if '..' in member_path:
                    return False
                
                # Check if the member path is within dest_path
                if not member_path.startswith(dest_path + os.sep) and member_path != dest_path:
                    return False
                
                # Extract the member
                member.extract(dest_path, member.name)
                
                # Check if the member was extracted outside dest_path
                if not member_path.startswith(dest_path + os.sep) and member_path != dest_path:
                    return False
            
            return True
            
    except (tarfile.TarError, OSError, ValueError):
        return False
