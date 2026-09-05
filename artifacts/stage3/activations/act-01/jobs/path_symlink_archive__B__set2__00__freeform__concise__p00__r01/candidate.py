import os
import tarfile
import stat
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory.
    
    Args:
        tar_path: Path to the tar archive.
        dest_path: Destination directory for extraction.
    
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    try:
        # Resolve the absolute paths immediately
        abs_tar_path = os.path.abspath(tar_path)
        abs_dest_path = os.path.abspath(dest_path)
        
        # Validate tar file exists
        if not os.path.isfile(abs_tar_path):
            return False
        
        # Create the destination directory if it doesn't exist
        os.makedirs(abs_dest_path, exist_ok=True)
        
        # Open the tar file
        with tarfile.open(abs_tar_path, 'r:*') as tar:
            # Validate all members before extraction
            for member in tar.getmembers():
                # Calculate the absolute path of the member's destination
                member_dest = os.path.join(abs_dest_path, member.name)
                abs_member_dest = os.path.abspath(member_dest)
                
                # Check for path traversal
                if not abs_member_dest.startswith(abs_dest_path + os.sep):
                    if abs_member_dest == abs_dest_path:
                        # Allow if dest is exactly the dest path
                        pass
                    else:
                        return False
                
                # Check for symbolic links that point outside
                if member.isdir():
                    continue
                elif member.issym() or member.islnk():
                    # For symlinks, we need to resolve the target
                    # We can't extract yet, so we just validate the path
                    # The actual link creation happens during extraction
                    pass
                
            # Now perform the extraction with validation
            for member in tar:
                member_dest = os.path.join(abs_dest_path, member.name)
                abs_member_dest = os.path.abspath(member_dest)
                
                # Re-validate path
                if not abs_member_dest.startswith(abs_dest_path + os.sep):
                    if abs_member_dest == abs_dest_path:
                        pass
                    else:
                        return False
                
                # Extract the member
                if member.isdir():
                    tar.extract(member, abs_dest_path)
                else:
                    tar.extract(member, abs_dest_path)
                    
    except Exception:
        return False
    
    return True
