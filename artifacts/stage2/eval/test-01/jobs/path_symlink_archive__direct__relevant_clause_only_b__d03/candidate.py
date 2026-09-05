import os
import tarfile
import tempfile

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict safety validation.
    Only creates symbolic links and hard links if the target remains within dest_path.
    Returns True on complete success, False otherwise.
    """
    try:
        # Ensure destination directory exists
        if not os.path.exists(dest_path):
            os.makedirs(dest_path)

        # Open the archive in read-only mode to prevent modification during extraction
        with tarfile.open(tar_path, 'r:*') as tar:
            # Validate all members before extraction
            for member in tar.getmembers():
                # Skip directories if necessary, but typically we want to extract them
                # Check if the member is a directory
                if member.isdir():
                    continue
                
                # Resolve the target path relative to the destination
                # For symlinks and hardlinks, we need to check the link target
                dest_member_path = os.path.normpath(os.path.join(dest_path, member.name))
                
                # Safety check: ensure the member name doesn't escape the destination
                # by checking if the normalized path starts with the destination
                if not dest_member_path.startswith(dest_path + os.sep) and dest_member_path != dest_path:
                    return False
                
                # Handle symlinks and hardlinks specifically
                if member.issym() or member.islnk():
                    # Resolve the link target
                    link_target = member.linkname
                    
                    # Normalize the link target
                    normalized_link_target = os.path.normpath(link_target)
                    
                    # If the link target is absolute, it must be inside dest_path
                    if os.path.isabs(normalized_link_target):
                        if not normalized_link_target.startswith(dest_path + os.sep) and normalized_link_target != dest_path:
                            return False
                    
                    # If the link target is relative, resolve it relative to the member's directory
                    if not os.path.isabs(normalized_link_target):
                        member_dir = os.path.dirname(dest_member_path)
                        resolved_link_target = os.path.normpath(os.path.join(member_dir, normalized_link_target))
                        
                        # Check if the resolved target is within dest_path
                        if not resolved_link_target.startswith(dest_path + os.sep) and resolved_link_target != dest_path:
                            return False
                    
                    # Create the directory structure if needed
                    if not os.path.exists(os.path.dirname(dest_member_path)):
                        os.makedirs(os.path.dirname(dest_member_path))
                    
                    # Create the symlink or hardlink
                    if member.issym():
                        os.symlink(link_target, dest_member_path)
                    else:
                        os.symlink(normalized_link_target, dest_member_path)
                
                elif member.isfile() or member.isdir():
                    # Create directory if it's a directory
                    if member.isdir():
                        os.makedirs(dest_member_path, exist_ok=True)
                    else:
                        # Create file
                        with open(dest_member_path, 'wb') as f:
                            f.write(member.fileobj)
                        # Set permissions if specified
                        if member.mode:
                            os.chmod(dest_member_path, member.mode)
            
            return True
            
    except Exception:
        return False
