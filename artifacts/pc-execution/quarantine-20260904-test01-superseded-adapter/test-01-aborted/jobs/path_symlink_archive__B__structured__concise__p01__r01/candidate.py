import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory.
    
    Security measures:
    - Validates all archive members before extraction.
    - Rejects symbolic links and hard links unless their fully resolved target remains within dest_path.
    - Ensures no archive content is written outside dest_path.
    
    Args:
        tar_path (str): Path to the tar archive.
        dest_path (str): Destination directory for extraction.
    
    Returns:
        bool: True if extraction completes successfully, False otherwise.
    """
    # Ensure dest_path exists and is a directory
    if not os.path.isdir(dest_path):
        return False
    
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Walk through all members and validate before extraction
            for member in tar.getmembers():
                # Resolve the member's target path
                if member.isdir():
                    target_path = os.path.join(dest_path, member.name)
                else:
                    target_path = os.path.join(dest_path, member.name)
                
                # Check for symbolic links and hard links
                if member.issym() or member.islnk():
                    # Resolve the link target
                    if member.issym():
                        link_target = member.linkname
                    else:
                        link_target = member.linkname
                    
                    # Resolve the link target relative to the archive's root
                    # and then resolve it relative to dest_path
                    resolved_link_target = os.path.normpath(os.path.join(dest_path, link_target))
                    
                    # Ensure the resolved link target is within dest_path
                    # Use os.path.commonpath to check if the resolved path is under dest_path
                    try:
                        common = os.path.commonpath([resolved_link_target, dest_path])
                        if common != dest_path:
                            return False
                    except ValueError:
                        return False
                
                # Validate the member's path is within dest_path
                # Normalize the member's path and resolve it relative to dest_path
                member_target = os.path.normpath(os.path.join(dest_path, member.name))
                
                # Ensure the member target is within dest_path
                try:
                    common = os.path.commonpath([member_target, dest_path])
                    if common != dest_path:
                        return False
                except ValueError:
                    return False
            
            # If all validations pass, proceed with extraction
            tar.extractall(path=dest_path)
            return True
    
    except Exception:
        return False
