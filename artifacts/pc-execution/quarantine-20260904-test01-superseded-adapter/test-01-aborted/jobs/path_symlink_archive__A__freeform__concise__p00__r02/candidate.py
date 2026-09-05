import os
import tarfile
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory with strict security checks.
    
    Args:
        tar_path: Path to the tar archive.
        dest_path: Destination directory for extraction.
        
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    try:
        # Normalize the destination path to remove any trailing slashes
        dest_path = os.path.normpath(dest_path)
        
        # Reject absolute paths
        if os.path.isabs(dest_path):
            raise ValueError("Destination path must be relative")
        
        # Resolve the absolute path of the destination
        resolved_dest = os.path.abspath(dest_path)
        
        # Check if the destination directory exists, create it if not
        if not os.path.exists(resolved_dest):
            try:
                os.makedirs(resolved_dest)
            except Exception:
                return False
        
        # Validate that the resolved destination is within the expected directory
        # Since we normalized the input, we just need to ensure it's valid
        # The plan says "raise an error if it escapes the resolved dest_path"
        # Since we are using the dest_path as the base, we need to ensure no
        # extraction goes outside of it. We'll do this during member validation.
        
        # Open the tar file
        tar = tarfile.open(tar_path, 'r:*')
        
        try:
            # Walk through each member of the archive
            for member in tar.getmembers():
                # Get the member's name relative to the destination
                member_name = member.name
                
                # Skip dot entries or entries that start with a dot (hidden files)
                # to prevent directory traversal attacks
                if member_name.startswith('.'):
                    continue
                
                # Resolve the target path
                target_path = os.path.normpath(os.path.join(resolved_dest, member_name))
                
                # Check for directory traversal
                if not target_path.startswith(resolved_dest):
                    return False
                
                # Check if the target path is outside the resolved destination
                # This is a double-check to ensure safety
                if not target_path.startswith(os.path.normpath(resolved_dest)):
                    return False
                
                # Check for symbolic links and hard links
                if member.issym() or member.islnk():
                    return False
                
                # Check for hard links
                if member.islnk():
                    return False
                
                # Create parent directories if necessary
                parent_dir = os.path.dirname(target_path)
                if not os.path.exists(parent_dir):
                    os.makedirs(parent_dir)
                
                # Extract the member
                if member.isdir():
                    os.makedirs(target_path)
                else:
                    tar.extract(member, path=resolved_dest)
        
        finally:
            tar.close()
        
        return True
        
    except Exception:
        return False
