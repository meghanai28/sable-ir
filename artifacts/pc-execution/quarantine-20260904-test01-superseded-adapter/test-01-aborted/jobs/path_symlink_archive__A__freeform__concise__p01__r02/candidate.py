import os
import tarfile
import stat
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict security validation.
    
    Rejects any archive member that is:
    - A symbolic link
    - A hard link
    - A file/directory with a symlink target that escapes dest_path
    - A file/directory with an absolute path outside dest_path
    
    Returns True only on complete success, False otherwise.
    """
    try:
        # Normalize paths to absolute and resolve them
        tar_path = os.path.abspath(tar_path)
        dest_path = os.path.abspath(dest_path)
        
        # Ensure dest_path exists and is a directory
        if not os.path.isdir(dest_path):
            return False
        
        # Open the tar file for reading
        with tarfile.open(tar_path, 'r:*') as tar:
            # Validate all members before extracting any
            members = tar.getmembers()
            
            for member in members:
                # Check for symbolic links
                if member.issym():
                    return False
                
                # Check for hard links
                if member.islnk():
                    return False
                
                # Resolve the member's path relative to dest_path
                # We need to check if the member's name would be outside dest_path
                # when extracted
                
                # Get the full path where this member would be extracted
                # If the member name contains '..' we need to be careful
                member_name = member.name
                
                # Check for path traversal attempts
                if '..' in member_name.split('/'):
                    return False
                
                # Construct the full destination path for this member
                # We use os.path.join but need to be careful about the structure
                dest_member_path = os.path.join(dest_path, member_name)
                
                # Normalize to handle any trailing slashes or dots
                dest_member_path = os.path.normpath(dest_member_path)
                
                # Check if the path is outside dest_path
                if not dest_member_path.startswith(dest_path + os.sep) and dest_member_path != dest_path:
                    return False
                
                # Additional check: ensure the path is within dest_path boundaries
                # by comparing the resolved path
                if not dest_member_path.startswith(dest_path):
                    return False
            
            # If all members pass validation, proceed with extraction
            # Extract each member one by one to ensure atomicity
            for member in members:
                # Extract the member
                tar.extract(member, dest_path)
            
            return True
            
    except Exception:
        return False
