import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination path with strict security validation.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory for extraction.
        
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    try:
        # Normalize and validate dest_path to ensure it stays within root
        dest_path = os.path.realpath(dest_path)
        if not dest_path.startswith(os.path.realpath('/')):
            return False
        
        # Open the tar file and extract members
        with tarfile.open(tar_path, 'r:*') as tar:
            # Validate and extract members
            for member in tar.getmembers():
                # Resolve the target path for the member
                member_dir = os.path.dirname(member.name)
                member_name = os.path.basename(member.name)
                
                # Construct the full path where the member would be extracted
                full_member_path = os.path.join(dest_path, member_dir, member_name)
                
                # Resolve the real path to check for escapes
                try:
                    real_member_path = os.path.realpath(full_member_path)
                except (OSError, ValueError):
                    return False
                
                # Check if the resolved path is within the destination
                if not real_member_path.startswith(os.path.realpath(dest_path) + os.sep) and real_member_path != os.path.realpath(dest_path):
                    return False
                
                # If it's a symbolic link, resolve the link target
                if member.issym:
                    link_target = member.linkname
                    # Resolve the link target relative to the member's location
                    link_target_path = os.path.join(dest_path, member_dir, link_target)
                    try:
                        real_link_target = os.path.realpath(link_target_path)
                    except (OSError, ValueError):
                        return False
                    
                    # Ensure the link target is within dest_path
                    if not real_link_target.startswith(os.path.realpath(dest_path) + os.sep) and real_link_target != os.path.realpath(dest_path):
                        return False
                
                # Extract the member
                tar.extract(member, dest_path)
            
            return True
            
    except Exception:
        return False
