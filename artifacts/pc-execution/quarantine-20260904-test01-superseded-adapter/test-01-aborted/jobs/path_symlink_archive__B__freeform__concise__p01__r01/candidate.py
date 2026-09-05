import os
import tarfile
import stat
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory with strict security checks.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory for extraction.
        
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    try:
        # Normalize the destination path immediately
        dest_path = os.path.normpath(dest_path)
        
        # Reject absolute paths
        if os.path.isabs(dest_path):
            return False
        
        # Create the destination directory if it doesn't exist
        os.makedirs(dest_path, exist_ok=True)
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get the list of members
            members = tar.getmembers()
            
            for member in members:
                # Resolve the member's name relative to the destination
                member_name = member.name
                
                # Skip . and ..
                if member_name == '.' or member_name == '..':
                    continue
                
                # Normalize the target path
                target_path = os.path.normpath(os.path.join(dest_path, member_name))
                
                # Check for escape attempts using ..
                if not target_path.startswith(dest_path + os.sep) and target_path != dest_path:
                    return False
                
                # Check for absolute paths in member names
                if os.path.isabs(member_name):
                    return False
                
                # Get the member's file mode
                member_mode = member.mode
                
                # Check for symbolic links or hard links
                if member.type == tarfile.SYMTYPE or member.type == tarfile.LINKTYPE:
                    # Resolve the target
                    target = member.linkname
                    
                    # Normalize the target
                    target_norm = os.path.normpath(target)
                    
                    # Check if the target escapes the destination
                    if not target_norm.startswith(dest_path + os.sep) and target_norm != dest_path:
                        return False
                    
                    # For symlinks, we need to ensure the target doesn't point outside
                    # We also need to check if the link itself would create a path outside
                    # The linkname check above handles the target, but we should also verify
                    # that the link target doesn't contain .. that would escape
                    if '..' in target_norm.split(os.sep):
                        return False
                    
                    # Create the link only if safe
                    try:
                        if member.type == tarfile.SYMTYPE:
                            os.symlink(target, target_path)
                        elif member.type == tarfile.LINKTYPE:
                            os.link(target, target_path)
                    except (OSError, ValueError):
                        return False
                    continue
                
                # Regular files or directories
                # Check if the parent directory exists
                parent_dir = os.path.dirname(target_path)
                if not os.path.exists(parent_dir):
                    os.makedirs(parent_dir, exist_ok=True)
                
                # Extract the member
                try:
                    tar.extract(member, dest_path)
                except (tarfile.TarError, OSError):
                    return False
            
            return True
            
    except Exception:
        return False
