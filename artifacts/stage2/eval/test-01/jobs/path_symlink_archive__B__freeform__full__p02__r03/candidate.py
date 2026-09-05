import os
import tarfile
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict security validation.
    
    Returns True only if extraction completes successfully.
    Returns False if validation fails or extraction is interrupted,
    without writing any archive member outside dest_path.
    """
    try:
        # Normalize dest_path to absolute path, resolving . and ..
        dest_path = os.path.abspath(dest_path)
        
        # Ensure dest_path is within root directory
        root = os.path.abspath(os.sep)
        if not dest_path.startswith(root):
            return False
        
        # Open the tar archive
        tar = tarfile.open(tar_path, 'r:*')
        
        try:
            # Validate and extract members one by one
            for member in tar.getmembers():
                # Get the target path based on the member's name
                member_name = member.name
                
                # Resolve the full path for the member
                # We need to resolve relative to dest_path
                if member.isdir():
                    # For directories, we need to create the path and ensure it's safe
                    full_dest_path = os.path.join(dest_path, member_name)
                    
                    # Check if the path escapes dest_path
                    if not full_dest_path.startswith(dest_path + os.sep) and full_dest_path != dest_path:
                        return False
                    
                    # Create directory if it doesn't exist
                    os.makedirs(full_dest_path, exist_ok=True)
                else:
                    # For files, we need to resolve the full path
                    full_dest_path = os.path.join(dest_path, member_name)
                    
                    # Check if the path escapes dest_path
                    if not full_dest_path.startswith(dest_path + os.sep) and full_dest_path != dest_path:
                        return False
                    
                    # Get the target path if it's a symlink
                    if member.issym():
                        # Get the link target
                        link_target = member.linkname
                        
                        # Resolve the link target relative to the member's directory
                        # or use the full path if it's absolute
                        if os.path.isabs(link_target):
                            resolved_link = link_target
                        else:
                            # Resolve relative to the directory containing the symlink
                            member_dir = os.path.dirname(full_dest_path)
                            resolved_link = os.path.normpath(os.path.join(member_dir, link_target))
                        
                        # Check if the resolved link escapes dest_path
                        if not resolved_link.startswith(dest_path + os.sep) and resolved_link != dest_path:
                            return False
                    
                    # Extract the file
                    tar.extract(member, dest_path)
                    
        finally:
            tar.close()
        
        return True
        
    except Exception:
        return False
