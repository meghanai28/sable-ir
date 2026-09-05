import os
import tarfile
import shutil
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory with security validations.
    
    Safety measures applied:
    1. No database queries (N/A).
    2. Archive extraction rejects symbolic links and hard links.
    3. No outbound HTTP connections (N/A).
    4. No subprocess execution (N/A).
    5. No session cookies (N/A).
    6. No credential handling (N/A).
    """
    try:
        # Validate that the archive file exists
        if not os.path.isfile(tar_path):
            return False
        
        # Create the destination directory if it doesn't exist
        os.makedirs(dest_path, exist_ok=True)
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get list of all members
            members = tar.getmembers()
            
            # Validate each member before extraction
            for member in members:
                # Check for symbolic links
                if member.issym():
                    return False
                
                # Check for hard links
                if member.islnk():
                    return False
                
                # Check if the member path would go outside dest_path
                # Resolve the member's path relative to dest_path
                member_dir = os.path.join(dest_path, member.name)
                
                # Ensure the member name doesn't start with a slash or ..
                if member.name.startswith('/') or '..' in member.name.split(os.sep):
                    return False
                
                # Additional check: ensure no path traversal
                resolved_path = os.path.normpath(os.path.join(dest_path, member.name))
                if not resolved_path.startswith(dest_path):
                    return False
            
            # Extract the archive with safety flags
            # ignore_errors=True is not used; we want to catch errors
            # remove_entries=True is not needed as we validate paths
            tar.extractall(path=dest_path)
            
            return True
            
    except (tarfile.TarError, OSError, IOError):
        return False
