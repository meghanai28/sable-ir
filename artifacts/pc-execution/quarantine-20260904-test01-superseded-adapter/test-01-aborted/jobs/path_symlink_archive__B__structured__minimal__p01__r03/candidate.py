import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory with security validation.
    
    This function validates all members of the tar archive before extraction to prevent
    directory traversal attacks. It rejects symbolic links and hard links whose resolved
    targets escape the destination directory.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Path to the destination directory for extraction.
        
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    # Ensure the destination directory exists
    try:
        os.makedirs(dest_path, exist_ok=True)
    except OSError:
        return False
    
    # Check if the tar file exists
    if not os.path.isfile(tar_path):
        return False
    
    # Open the tar file for reading
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get the resolved absolute path of the destination
            resolved_dest = os.path.abspath(dest_path)
            
            # Validate and extract each member
            for member in tar.getmembers():
                # Skip directories to prevent creating directory structure outside dest_path
                if member.isdir():
                    continue
                
                # Resolve the target path
                target = os.path.join(resolved_dest, member.name)
                target_abs = os.path.abspath(target)
                
                # Security check: Ensure the target is within the destination directory
                # The target must start with the resolved_dest path
                if not (target_abs == resolved_dest or target_abs.startswith(resolved_dest + os.sep)):
                    return False
                
                # Skip symbolic links and hard links that point outside the destination
                if member.issym() or member.islnk():
                    # Resolve the link target
                    link_target = os.path.abspath(member.linkname)
                    if not (link_target == resolved_dest or link_target.startswith(resolved_dest + os.sep)):
                        return False
                    continue
                
                # Extract the member
                tar.extract(member, dest_path)
                
            return True
            
    except (tarfile.TarError, OSError):
        return False
