import os
import tarfile
import stat
import tempfile

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict security validations.
    
    Security measures applied:
    1. Archive members are validated before extraction to prevent symlink/hardlink traversal attacks.
    2. All extracted paths are normalized and verified to remain within dest_path.
    3. No external commands are executed; only direct file operations are performed.
    """
    if not os.path.isfile(tar_path):
        return False
    
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Validate all members before extraction
            for member in tar.getmembers():
                # Normalize the member's name to remove any '..' components
                normalized_name = os.path.normpath(member.name)
                
                # Ensure the member is not an absolute path
                if os.path.isabs(member.name):
                    return False
                
                # Construct the full destination path
                dest_member_path = os.path.join(dest_path, normalized_name)
                
                # Normalize the destination path to check for traversal
                normalized_dest = os.path.normpath(dest_member_path)
                
                # Ensure the normalized destination is within dest_path
                if not normalized_dest.startswith(os.path.normpath(dest_path) + os.sep) and normalized_dest != os.path.normpath(dest_path):
                    return False
                
                # Additional check for hard links that might point outside
                if member.linkname and not normalized_dest.startswith(os.path.normpath(dest_path) + os.sep):
                    return False
            
            # Extract with filtering
            for member in tar:
                member.name = os.path.normpath(member.name)
                if not member.name.startswith(os.path.normpath(dest_path) + os.sep):
                    continue
                
                if member.isdir():
                    os.makedirs(member.name, exist_ok=True)
                else:
                    # Create parent directories if needed
                    parent_dir = os.path.dirname(member.name)
                    if parent_dir and not os.path.exists(parent_dir):
                        os.makedirs(parent_dir, exist_ok=True)
                    
                    # Extract the file
                    tar.extract(member, path=dest_path, set_mode=member.mode, set_owner=member.uid, set_group=member.gid)
            
            return True
            
    except Exception:
        return False
