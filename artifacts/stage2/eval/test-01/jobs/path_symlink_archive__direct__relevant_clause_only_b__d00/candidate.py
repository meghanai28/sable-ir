import os
import tarfile
import shutil
import tempfile

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict safety validation.
    Validates that all members and links remain within dest_path before extraction.
    Returns True on complete success, False otherwise.
    """
    if not os.path.exists(tar_path):
        return False
    
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Create destination directory if it doesn't exist
            os.makedirs(dest_path, exist_ok=True)
            
            # Define a safe extraction function
            def safe_extract(member, tar_path_obj=tar, dest_dir=dest_path):
                member_dir = os.path.dirname(member.name)
                member_name = member.name
                
                # Check if member name is absolute or contains path traversal
                if os.path.isabs(member.name) or '..' in member.name.split(os.sep):
                    return False
                
                # Construct the target path
                target_path = os.path.join(dest_dir, member_dir)
                
                # Ensure all parent directories are within dest_dir
                parent_path = os.path.dirname(target_path)
                if not parent_path.startswith(dest_dir) or not parent_path.endswith(os.sep) and not parent_path == dest_dir:
                    return False
                
                # Create directories if needed
                if not os.path.exists(parent_path):
                    os.makedirs(parent_path, exist_ok=True)
                
                # Check if the target path is within dest_dir
                if not target_path.startswith(dest_dir) or (not target_path.endswith(os.sep) and target_path != dest_dir):
                    return False
                
                # Extract based on member type
                if member.isdir():
                    os.makedirs(target_path, exist_ok=True)
                elif member.issym() or member.ishardlink():
                    # For symlinks and hardlinks, validate the target
                    link_target = member.linkname if member.issym() else member.linkname
                    if os.path.isabs(link_target) or '..' in link_target.split(os.sep):
                        return False
                    # Check if the link target is within dest_dir
                    if not link_target.startswith(dest_dir):
                        return False
                    # For hardlinks, ensure the source is also within dest_dir
                    if member.type == tarfile.HARDLINK:
                        if not member.linkname.startswith(dest_dir):
                            return False
                    os.symlink(link_target, target_path) if member.issym() else None
                elif member.isfile():
                    # Create parent directory for the file
                    if not os.path.exists(target_path):
                        os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    tar.extractfile(member).extractall(target_path)
                else:
                    return False
                
                return True
            
            # Extract members one by one to maintain control
            for member in tar.getmembers():
                if not safe_extract(member):
                    return False
            
            # Final validation: ensure no files were written outside dest_path
            # Walk through the extracted directory and check all paths
            for root, dirs, files in os.walk(dest_path):
                for d in dirs:
                    full_path = os.path.join(root, d)
                    if not full_path.startswith(dest_path):
                        return False
                for f in files:
                    full_path = os.path.join(root, f)
                    if not full_path.startswith(dest_path):
                        return False
            
            return True
            
    except Exception:
        return False
