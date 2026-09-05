import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path, rejecting any symbolic links or hard links.
    Returns True only if extraction completes successfully with all members validated.
    """
    try:
        # Ensure dest_path exists and is a directory
        if not os.path.isdir(dest_path):
            return False
        
        with tarfile.open(tar_path, 'r:*') as tar:
            for member in tar.getmembers():
                # Skip if the member is a symlink or hardlink
                if member.type == tarfile.SYMLINK_TYPE or member.type == tarfile.HARDLINK:
                    return False
                
                # Calculate the target path relative to dest_path
                target_path = os.path.normpath(os.path.join(dest_path, member.name))
                
                # Resolve the real path to detect traversal attempts
                # We need to check if the resolved path is outside dest_path
                # Note: member.name might contain .. but we resolve it
                resolved_target = os.path.realpath(target_path)
                
                # Ensure the resolved target is within dest_path
                # os.path.commonpath might not work perfectly with symlinks, so we use is_relative_to in Python 3.9+
                # For broader compatibility, we check if resolved_target starts with dest_path + os.sep or is dest_path itself
                dest_path_resolved = os.path.realpath(dest_path)
                
                # Handle cases where dest_path is a symlink
                if not resolved_target.startswith(dest_path_resolved + os.sep) and resolved_target != dest_path_resolved:
                    return False
                
                # Check if the parent directory exists, create if not
                parent_dir = os.path.dirname(target_path)
                if parent_dir and not os.path.exists(parent_dir):
                    os.makedirs(parent_dir)
                
                # Extract the member
                if member.isdir():
                    os.makedirs(target_path)
                else:
                    # Extract file content
                    tar.extract(member, dest_path)
        
        return True
    
    except Exception:
        return False
