import os
import tarfile
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory, ensuring no files escape dest_path.
    
    Args:
        tar_path: Path to the tar archive.
        dest_path: Destination directory for extraction.
    
    Returns:
        True if extraction completes successfully; False otherwise.
    """
    try:
        # Resolve the destination path and ensure it's absolute
        resolved_dest = os.path.abspath(dest_path)
        
        # Normalize the destination path to remove any .. or . components
        normalized_dest = os.path.normpath(resolved_dest)
        
        # Ensure the destination directory exists
        os.makedirs(normalized_dest, exist_ok=True)
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Iterate over each member in the tar file
            for member in tar.getmembers():
                # Get the relative path of the member from the destination
                member_name = member.name
                
                # Skip if the member name is empty or contains '..'
                if not member_name or '..' in member_name.split(os.sep):
                    continue
                
                # Calculate the target path for the member
                target_path = os.path.join(normalized_dest, member_name)
                
                # Resolve the target path to check for path traversal
                resolved_target = os.path.normpath(os.path.abspath(target_path))
                
                # Ensure the resolved target is within the normalized destination
                if not resolved_target.startswith(normalized_dest + os.sep) and resolved_target != normalized_dest:
                    return False
                
                # Extract the member
                try:
                    tar.extract(member, path=normalized_dest)
                except Exception:
                    return False
                
                # Check for symbolic links that might point outside the destination
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    resolved_link_target = os.path.normpath(os.path.abspath(os.path.join(normalized_dest, link_target)))
                    if not resolved_link_target.startswith(normalized_dest + os.sep) and resolved_link_target != normalized_dest:
                        return False
        
        return True
    
    except Exception:
        return False
