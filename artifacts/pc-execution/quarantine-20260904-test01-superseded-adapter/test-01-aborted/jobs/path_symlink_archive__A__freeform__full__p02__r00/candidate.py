import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory with security checks.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory for extraction.
        
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    try:
        # Resolve the absolute path of the destination
        resolved_dest = os.path.realpath(dest_path)
        
        # Ensure the destination directory exists
        if not os.path.isdir(resolved_dest):
            os.makedirs(resolved_dest, exist_ok=True)
        
        # Open the tar file in read-only mode
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get list of all members
            members = tar.getnames()
            
            for member in members:
                # Skip directories (they are created automatically, but we need to check files)
                if member.endswith('/'):
                    continue
                
                # Check for symbolic links
                if member.islnk():
                    # Reject symbolic links regardless of target
                    return False
                
                # Check for hard links
                if member.issym() or member.islnk():
                    # Already handled above, but for hard links specifically:
                    if member.islnk():
                        return False
                
                # For regular files and directories, check the path
                # We need to resolve the member's path relative to the archive root
                # and check if it would escape the destination
                
                # Get the member's arcname
                arcname = member.name
                
                # Check if the arcname contains path traversal
                if '..' in arcname.split(os.sep):
                    return False
                
                # Construct the full destination path for this member
                # We need to handle the case where the member is a directory or file
                dest_member_path = os.path.join(resolved_dest, arcname)
                
                # Normalize the path to resolve any .. or . components
                # This helps in detecting path traversal attempts
                normalized_dest_member = os.path.normpath(dest_member_path)
                
                # Ensure the normalized path is still within the destination
                if not normalized_dest_member.startswith(resolved_dest + os.sep) and normalized_dest_member != resolved_dest:
                    return False
                
                # Extract the member
                tar.extract(member, resolved_dest, set_attrs=False)
            
            return True
            
    except Exception:
        return False
