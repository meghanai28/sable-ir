import os
import tarfile
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory with strict path validation.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory for extraction.
        
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    try:
        # Normalize and validate dest_path to ensure it stays within root
        dest_path = os.path.realpath(dest_path)
        
        # Check if dest_path is outside root directory
        if not dest_path.startswith(os.sep) and dest_path != '/':
            return False
            
        # Ensure dest_path exists and is a directory
        if not os.path.isdir(dest_path):
            return False
            
        # Create dest_path if it doesn't exist
        os.makedirs(dest_path, exist_ok=True)
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get the root directory for validation
            root_dir = os.path.realpath(dest_path)
            
            for member in tar.getmembers():
                # Resolve the member's path relative to the root
                member_path = os.path.join(root_dir, member.name)
                
                # Resolve the symbolic link target if it's a link
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    # Resolve the link target to check for traversal
                    resolved_link = os.path.realpath(os.path.join(root_dir, member.name))
                    
                    # Check if the resolved path is outside the root
                    if not resolved_link.startswith(root_dir) and resolved_link != root_dir:
                        return False
                else:
                    # For regular files and directories, check if the path is within root
                    if not member_path.startswith(root_dir) and member_path != root_dir:
                        return False
                
                # Extract the member
                try:
                    tar.extract(member, dest_path)
                except Exception:
                    return False
                    
        return True
        
    except Exception:
        return False
