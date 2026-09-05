import os
import tarfile
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory with strict security validation.
    
    This function:
    1. Normalizes and validates the destination path to ensure it stays within the root.
    2. Walks through each member of the tar archive.
    3. Validates file types, permissions, and symbolic links.
    4. Ensures no archive member or symbolic link target escapes the destination directory.
    5. Extracts the archive only if all validations pass.
    
    Returns:
        bool: True if extraction completes successfully, False otherwise.
    """
    try:
        # Normalize the destination path to remove any trailing slashes or relative components
        # Ensure it's an absolute path
        if not os.path.isabs(dest_path):
            dest_path = os.path.abspath(dest_path)
        
        # Create the destination directory if it doesn't exist
        os.makedirs(dest_path, exist_ok=True)
        
        # Normalize the destination path to ensure it's the same as the realpath
        # This prevents attacks where dest_path is a symlink to a different location
        dest_path_real = os.path.realpath(dest_path)
        
        # Check if the destination path escapes the root directory
        if not dest_path_real.startswith(os.path.realpath('/')):
            # If the path is not absolute or escapes the root, return False
            return False
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get all members of the tar archive
            members = tar.getmembers()
            
            # Validate each member
            for member in members:
                # Get the absolute path of the member
                member_dir = os.path.dirname(member.name)
                member_file = os.path.basename(member.name)
                
                # Check if the member is a directory
                if member.isdir():
                    # Ensure the directory path doesn't escape the destination
                    if not member_dir.startswith(dest_path_real):
                        return False
                else:
                    # Ensure the file path doesn't escape the destination
                    if not member.name.startswith(dest_path_real):
                        return False
                
                # Check for symbolic links
                if member.issym() or member.islnk():
                    # Get the link target
                    link_target = member.linkname
                    
                    # Resolve the link target relative to the member's directory
                    if member.isdir():
                        link_target = os.path.join(member_dir, link_target)
                    else:
                        link_target = os.path.join(os.path.dirname(member.name), link_target)
                    
                    # Normalize the link target to remove any relative components
                    link_target = os.path.normpath(link_target)
                    
                    # Ensure the link target doesn't escape the destination
                    if not link_target.startswith(dest_path_real):
                        return False
                    
                    # Check if the link target is a symlink
                    if os.path.islink(link_target):
                        # Resolve the symlink target
                        resolved_target = os.path.realpath(link_target)
                        
                        # Ensure the resolved target doesn't escape the destination
                        if not resolved_target.startswith(dest_path_real):
                            return False
                
                # Check if the member is a hard link
                if member.islnk():
                    # Get the link target
                    link_target = member.linkname
                    
                    # Resolve the link target relative to the member's directory
                    if member.isdir():
                        link_target = os.path.join(member_dir, link_target)
                    else:
                        link_target = os.path.join(os.path.dirname(member.name), link_target)
                    
                    # Normalize the link target to remove any relative components
                    link_target = os.path.normpath(link_target)
                    
                    # Ensure the link target doesn't escape the destination
                    if not link_target.startswith(dest_path_real):
                        return False
                    
                    # Check if the link target is a symlink
                    if os.path.islink(link_target):
                        # Resolve the symlink target
                        resolved_target = os.path.realpath(link_target)
                        
                        # Ensure the resolved target doesn't escape the destination
                        if not resolved_target.startswith(dest_path_real):
                            return False
            
            # If all validations pass, extract the archive
            tar.extractall(dest_path)
            
            return True
    
    except Exception:
        return False
