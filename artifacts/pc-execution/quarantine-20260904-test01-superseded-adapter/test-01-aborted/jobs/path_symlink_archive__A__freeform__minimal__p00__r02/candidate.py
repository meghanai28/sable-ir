import os
import tarfile
import shutil
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory with safety checks.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory for extraction.
        
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    try:
        # Normalize the destination path to remove any trailing slashes or . segments
        # but keep the directory structure intact for validation purposes
        dest_path = os.path.normpath(dest_path)
        
        # Check if dest_path is absolute
        if os.path.isabs(dest_path):
            raise ValueError("dest_path must be a relative path")
        
        # Create the destination directory if it doesn't exist
        os.makedirs(dest_path, exist_ok=True)
        
        # Resolve the actual path of the destination directory
        resolved_dest = os.path.realpath(dest_path)
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Iterate over all members in the archive
            for member in tar.getmembers():
                # Skip symbolic links and hard links
                if member.issym() or member.islnk():
                    continue
                
                # Check if the member is a regular file or directory
                if not (member.isfile() or member.isdir()):
                    continue
                
                # Calculate the target path for this member
                target_path = os.path.join(resolved_dest, member.name)
                
                # Normalize the target path to remove any .. or . segments
                normalized_target = os.path.normpath(target_path)
                
                # Resolve the actual path to check for escape attempts
                resolved_target = os.path.realpath(normalized_target)
                
                # Ensure the resolved target is within the resolved destination
                if not resolved_target.startswith(resolved_dest + os.sep) and resolved_target != resolved_dest:
                    raise ValueError(f"Archive member {member.name} would escape the destination directory")
                
                # Extract the member
                tar.extract(member, dest_path)
        
        return True
        
    except Exception:
        return False
