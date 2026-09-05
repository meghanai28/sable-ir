import os
import tarfile
import stat
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination path, ensuring no extraction
    occurs outside the intended destination directory.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory where the archive should be extracted.
        
    Returns:
        True if extraction completes successfully without escaping the destination.
        False if any validation or extraction fails.
    """
    # Normalize the destination path to an absolute path
    dest_path = os.path.abspath(dest_path)
    
    # Create the destination directory if it doesn't exist
    os.makedirs(dest_path, exist_ok=True)
    
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Iterate over all members in the tar archive
            for member in tar.getmembers():
                # Normalize the member's name relative to the destination
                member_dir = os.path.dirname(member.name)
                member_name = os.path.basename(member.name)
                
                # Construct the full path for the member relative to the destination
                # We use the member's name as a string to avoid path traversal
                # First, resolve the directory part relative to dest_path
                if member_dir:
                    safe_dir = os.path.normpath(os.path.join(dest_path, member_dir))
                else:
                    safe_dir = dest_path
                
                # Ensure the directory is within the destination
                if not safe_dir.startswith(dest_path + os.sep) and safe_dir != dest_path:
                    return False
                
                # Resolve the full path for the member
                if member.isdir():
                    full_path = safe_dir + os.sep + member_name
                else:
                    full_path = safe_dir + os.sep + member_name
                
                # Check if the full path escapes the destination
                if not full_path.startswith(dest_path + os.sep) and full_path != dest_path:
                    return False
                
                # Check for symlinks that might escape the destination
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    # Normalize the link target to resolve .. segments
                    normalized_link = os.path.normpath(link_target)
                    # Resolve the link target relative to the member's directory
                    if member_dir:
                        resolved_link = os.path.normpath(os.path.join(safe_dir, normalized_link))
                    else:
                        resolved_link = os.path.normpath(os.path.join(dest_path, normalized_link))
                    
                    # Ensure the resolved link target is within the destination
                    if not resolved_link.startswith(dest_path + os.sep) and resolved_link != dest_path:
                        return False
                
                # Extract the member
                tar.extract(member, dest_path)
                
    except Exception:
        return False
    
    return True
