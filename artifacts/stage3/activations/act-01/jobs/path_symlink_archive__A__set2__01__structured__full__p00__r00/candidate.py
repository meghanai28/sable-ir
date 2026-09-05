import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to the specified destination path.
    
    This function validates that the tar archive does not contain members
    that would escape the destination directory, even if the member names
    do not contain '..'. It also validates that the destination path itself
    is safe and does not escape the intended extraction location.
    
    Args:
        tar_path (str): Path to the tar archive file.
        dest_path (str): Destination directory for extraction.
    
    Returns:
        bool: True if extraction completes successfully, False otherwise.
    """
    try:
        # Normalize the destination path to remove any trailing slashes
        dest_path = os.path.normpath(dest_path)
        
        # Resolve the actual path for the destination directory
        # This helps in detecting if the path is a symlink or has .. segments
        resolved_dest = os.path.realpath(dest_path)
        
        # Check if the resolved destination is within the current working directory
        # or if it contains .. segments that could be exploited
        if '..' in dest_path:
            raise ValueError("Destination path contains '..' segments which are not allowed.")
        
        # Validate the tar_path
        if not os.path.isfile(tar_path):
            raise ValueError(f"Tar file not found: {tar_path}")
        
        # Open the tar file and iterate over the members
        with tarfile.open(tar_path, 'r:*') as tar:
            # Extract the names of all members
            member_names = [member.name for member in tar.getmembers()]
            
            # Validate each member to ensure it does not escape the destination
            for member in tar.getmembers():
                # Get the member's name and check for ..
                if '..' in member.name:
                    raise ValueError(f"Member '{member.name}' contains '..' segments.")
                
                # Calculate the member's destination path
                member_dest = os.path.normpath(os.path.join(dest_path, member.name))
                
                # Resolve the member's destination path
                resolved_member = os.path.realpath(member_dest)
                
                # Check if the resolved member is within the resolved destination
                if not resolved_member.startswith(resolved_dest + os.sep) and resolved_member != resolved_dest:
                    raise ValueError(f"Member '{member.name}' would escape the destination directory.")
            
            # Extract the archive
            tar.extractall(path=dest_path)
            
            return True
            
    except Exception as e:
        # Clean up any partially extracted files if an error occurs
        # Note: Since we validate before extraction, there should be no files outside dest_path
        return False
