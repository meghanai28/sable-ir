import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict security guards.
    
    Returns True only if extraction completes successfully without writing outside dest_path.
    Returns False if validation fails, extraction fails, or any member would write outside dest_path.
    """
    try:
        # Ensure dest_path exists
        os.makedirs(dest_path, exist_ok=True)
        
        # Open the archive
        with tarfile.open(tar_path, 'r:*') as tar:
            # Validate all members before extraction
            for member in tar.getmembers():
                # Calculate the full destination path for this member
                dest_member_path = os.path.normpath(os.path.join(dest_path, member.name))
                
                # Check for absolute paths or paths that escape dest_path
                if os.path.isabs(member.name):
                    return False
                
                # Normalize the member name to remove .. components
                normalized_name = os.path.normpath(member.name)
                
                # Check if the normalized path escapes dest_path
                # This handles cases like "../" or "./"
                if not normalized_name.startswith(os.path.normpath(dest_path) + os.sep) and not (normalized_name == os.path.normpath(dest_path)):
                    return False
                
                # Additional check: ensure the member name doesn't start with ..
                if normalized_name.startswith('..'):
                    return False
                
                # Check for symbolic links and hard links
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    # Normalize the link target
                    normalized_link_target = os.path.normpath(link_target)
                    
                    # If the link target is absolute, reject it
                    if os.path.isabs(link_target):
                        return False
                    
                    # If the link target is relative, ensure it stays within dest_path
                    # When resolved against dest_path, it should not escape
                    if not normalized_link_target.startswith(os.path.normpath(dest_path) + os.sep) and not (normalized_link_target == os.path.normpath(dest_path)):
                        return False
                    
                    # Also check if the link target contains ..
                    if '..' in normalized_link_target.split(os.sep):
                        return False
                
                # Check for hard links
                if member.islnk():
                    link_target = member.linkname
                    # Normalize the link target
                    normalized_link_target = os.path.normpath(link_target)
                    
                    # If the link target is absolute, reject it
                    if os.path.isabs(link_target):
                        return False
                    
                    # If the link target is relative, ensure it stays within dest_path
                    if not normalized_link_target.startswith(os.path.normpath(dest_path) + os.sep) and not (normalized_link_target == os.path.normpath(dest_path)):
                        return False
                    
                    # Also check if the link target contains ..
                    if '..' in normalized_link_target.split(os.sep):
                        return False
            
            # If all validations pass, extract the archive
            # Use extractall to extract all members at once
            tar.extractall(dest_path)
            
            return True
            
    except Exception:
        return False
