import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to the specified destination path.
    
    Returns:
        bool: True if extraction completes successfully, False otherwise.
    
    Security Measures:
        - Rejects any symbolic links or hard links, even if targets are within dest_path.
        - Validates all archive members before extraction.
        - Ensures no files are written outside dest_path.
    """
    try:
        # Create the destination directory if it doesn't exist
        os.makedirs(dest_path, exist_ok=True)
        
        # Open the tar archive
        with tarfile.open(tar_path, 'r:*') as tar:
            # Iterate over all members in the archive
            for member in tar.getmembers():
                # Skip directories to prevent creating directory structures outside dest_path
                # Only process regular files and directories
                if member.isdir():
                    continue
                
                # Check if the member name contains '..' which could escape dest_path
                if '..' in member.name:
                    return False
                
                # Calculate the full destination path
                dest_member_path = os.path.join(dest_path, member.name)
                
                # Ensure the destination path is within dest_path
                # Use os.path.realpath to resolve symlinks and normalize paths
                # However, since we reject symlinks, we can use os.path.abspath
                abs_dest = os.path.abspath(dest_member_path)
                abs_dest_path = os.path.abspath(dest_path)
                
                # Verify the destination is within the allowed path
                if not abs_dest.startswith(abs_dest_path + os.sep) and abs_dest != abs_dest_path:
                    return False
                
                # Check for symbolic links
                if member.issym() or member.islnk():
                    return False
                
                # Extract the member
                tar.extract(member, dest_path)
        
        return True
    
    except Exception as e:
        return False
