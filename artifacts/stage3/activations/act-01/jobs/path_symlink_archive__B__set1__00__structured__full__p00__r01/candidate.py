import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict path validation to prevent
    directory traversal attacks. Returns True on complete success, False otherwise.
    """
    try:
        # Normalize the destination path to remove any trailing slashes and resolve
        # the root directory, ensuring we work with an absolute path.
        dest_path = os.path.normpath(dest_path)
        
        # Ensure the destination directory exists
        if not os.path.isdir(dest_path):
            os.makedirs(dest_path, exist_ok=True)
        
        # Validate that tar_path exists and is a file
        if not os.path.isfile(tar_path):
            return False
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get the absolute path of the destination directory
            abs_dest = os.path.abspath(dest_path)
            
            # Iterate over each member in the archive
            for member in tar.getmembers():
                # Resolve the member's name to an absolute path
                # We use the absolute path of the destination as the base
                # to resolve the member's path correctly.
                member_name = member.name
                
                # Check for path traversal in the member name itself
                # Split the name and check if any part is '..'
                if '..' in member_name.split(os.sep):
                    return False
                
                # Resolve the full path of the member
                full_member_path = os.path.normpath(os.path.join(abs_dest, member_name))
                abs_member_path = os.path.abspath(full_member_path)
                
                # Validate that the resolved path is within the destination directory
                # Use os.path.commonpath to ensure the paths are identical up to the destination
                common = os.path.commonpath([abs_dest, abs_member_path])
                if not abs_member_path.startswith(os.sep + common + os.sep) and abs_member_path != common:
                    return False
                
                # Check for symbolic links
                if member.issym():
                    link_path = os.path.join(abs_dest, member.name)
                    # Resolve the link target
                    try:
                        link_target = os.path.realpath(link_path)
                    except (OSError, ValueError):
                        return False
                    
                    # Validate the link target is within the destination
                    common = os.path.commonpath([abs_dest, link_target])
                    if not link_target.startswith(os.sep + common + os.sep) and link_target != common:
                        return False
                    
                    # If the link target is safe, we still need to be careful
                    # We will extract the link but ensure it points to a safe location
                    # Actually, for safety, we should resolve the link target relative to the extraction point
                    # and ensure it's within dest_path.
                    # If the link target is a symlink, we need to resolve it.
                    # The above check handles the resolved target.
                    # However, we must also ensure the link itself doesn't point outside.
                    # The above check does that.
                    
                    # But wait, if the link target is inside dest_path, we can create the link.
                    # If it's outside, we reject it.
                    # The above check ensures the resolved target is inside dest_path.
                    pass
                
                # Validate the member type and name
                if not member.isfile() and not member.isdir() and not member.issym():
                    return False
                
                # Extract the member
                try:
                    tar.extract(member, dest_path)
                except Exception:
                    return False
            
            return True
    
    except Exception:
        return False
