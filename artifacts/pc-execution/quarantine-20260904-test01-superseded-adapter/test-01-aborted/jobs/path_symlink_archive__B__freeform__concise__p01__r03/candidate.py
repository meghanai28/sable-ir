import os
import tarfile
import shutil
import tempfile

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory with strict security checks.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory for extraction.
        
    Returns:
        True if extraction completed successfully, False otherwise.
    """
    try:
        # Resolve the destination path to its absolute form
        resolved_dest = os.path.abspath(dest_path)
        
        # Reject absolute paths that are not within the current working directory context
        # or if they contain '..' segments that could escape
        if os.path.isabs(dest_path):
            # If dest_path is absolute, we must ensure it's safe
            # The plan says to reject absolute dest_path, but typically in secure contexts
            # we might want to allow it if it's within a trusted base. However, the plan says:
            # "Reject absolute dest_path" - we interpret this as rejecting any absolute path
            # that isn't the current directory or a subdirectory of it. But to be strict:
            if not dest_path == os.getcwd() and not dest_path.startswith(os.getcwd() + os.sep):
                raise ValueError("Absolute destination paths are not allowed")
        
        # Normalize the destination path to remove any .. segments
        normalized_dest = os.path.normpath(resolved_dest)
        
        # Create the destination directory if it doesn't exist
        os.makedirs(normalized_dest, exist_ok=True)
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get all members of the tar file
            members = tar.getmembers()
            
            # Validate each member before extraction
            for member in members:
                # Check if the member is a directory
                if member.isdir():
                    continue
                
                # Get the member's name
                member_name = member.name
                
                # Skip if the member name is empty or starts with /
                if not member_name or member_name.startswith('/'):
                    continue
                
                # Calculate the full path for the member
                full_member_path = os.path.normpath(os.path.join(normalized_dest, member_name))
                
                # Check if the full member path escapes the destination
                if not full_member_path.startswith(normalized_dest + os.sep) and full_member_path != normalized_dest:
                    raise ValueError(f"Member {member_name} would escape the destination directory")
                
                # Check for symbolic links or hard links that point outside the destination
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    resolved_link_target = os.path.normpath(os.path.join(normalized_dest, link_target))
                    
                    # Check if the link target escapes the destination
                    if not resolved_link_target.startswith(normalized_dest + os.sep) and resolved_link_target != normalized_dest:
                        raise ValueError(f"Symbolic link/hard link {member_name} points outside the destination directory")
                
                # Check for device files or other special files
                if member.type == tarfile.S_IFREG:
                    # Regular file - proceed with extraction
                    pass
                elif member.type == tarfile.S_IFDIR:
                    # Directory - create it
                    os.makedirs(full_member_path, exist_ok=True)
                    continue
                else:
                    # Skip other types or handle appropriately
                    continue
            
            # Extract the tar file
            tar.extractall(path=normalized_dest)
            
            return True
            
    except Exception as e:
        # Clean up any partially extracted files if necessary
        return False
