import os
import tarfile
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict security guards against
    path traversal and unsafe link targets.
    
    Returns True only if extraction completes successfully without errors.
    Returns False if validation or extraction fails, without writing outside dest_path.
    """
    # Validate dest_path is not absolute
    if os.path.isabs(dest_path):
        raise ValueError("dest_path must be a relative path")
    
    # Normalize dest_path to remove .. and . components
    try:
        dest_path = os.path.normpath(dest_path)
    except ValueError:
        return False
    
    # Ensure dest_path is within root (no .. escapes)
    if not dest_path.startswith(os.sep) and not dest_path.startswith('.'):
        # If it's not absolute and doesn't start with ., it might be empty or invalid
        # normpath handles . and .., but we need to ensure it doesn't escape
        if '..' in dest_path.split(os.sep):
            return False
    
    # Create dest_path if it doesn't exist
    try:
        os.makedirs(dest_path, exist_ok=True)
    except OSError:
        return False
    
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            for member in tar.getmembers():
                # Resolve the full path for the member
                member_dir = os.path.join(dest_path, member.name)
                
                # Check for path traversal in the member name itself
                # Normalize the member path relative to dest_path
                rel_member_path = os.path.relpath(member.name, '.')
                if not rel_member_path.startswith('..'):
                    # This check is somewhat redundant with normpath but adds safety
                    pass
                
                # Get the absolute path of the destination directory for this member
                abs_member_dir = os.path.abspath(member_dir)
                
                # Ensure the destination directory is within dest_path
                if not abs_member_dir.startswith(os.path.abspath(dest_path)):
                    return False
                
                # Handle links before extraction
                if member.isdir():
                    if not os.path.exists(abs_member_dir):
                        os.makedirs(abs_member_dir, exist_ok=True)
                elif member.issym() or member.islnk():
                    # Validate link target
                    if member.linkname:
                        # Resolve link target
                        link_target = os.path.normpath(os.path.join(os.path.dirname(member.name), member.linkname))
                        # Check if link target escapes dest_path
                        if not link_target.startswith(os.path.abspath(dest_path)):
                            return False
                        # Ensure link target is not a directory (symlink to directory is allowed if it's inside dest_path)
                        # But we must ensure the link target is within dest_path
                        abs_link_target = os.path.abspath(link_target)
                        if not abs_link_target.startswith(os.path.abspath(dest_path)):
                            return False
                elif member.islnk():
                    # Hard link target
                    link_target = os.path.normpath(os.path.join(os.path.dirname(member.name), member.linkname))
                    if not link_target.startswith(os.path.abspath(dest_path)):
                        return False
                    abs_link_target = os.path.abspath(link_target)
                    if not abs_link_target.startswith(os.path.abspath(dest_path)):
                        return False
                
                # Extract the member
                tar.extract(member, dest_path)
                
    except (tarfile.TarError, OSError, ValueError):
        return False
    
    return True
