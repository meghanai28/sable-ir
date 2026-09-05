import os
import tarfile
import stat
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory with strict security validation.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory where the archive should be extracted.
        
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    # Normalize the destination path to remove trailing slashes and resolve basic path issues
    dest_path = os.path.normpath(dest_path)
    
    # Ensure the destination directory exists
    if not os.path.isdir(dest_path):
        try:
            os.makedirs(dest_path, exist_ok=True)
        except Exception:
            return False
    
    # Validate that dest_path does not contain '..' segments that could escape
    # We check the resolved path against the original normalized path
    resolved_dest = os.path.realpath(dest_path)
    if not resolved_dest.startswith(os.path.normpath(dest_path)):
        return False
    
    # Open the tar archive
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get the list of members to validate before extraction
            members = tar.getmembers()
            
            for member in members:
                # Skip directories (mode 0o40000)
                if member.isdir():
                    continue
                
                # Check if the member name is absolute
                if os.path.isabs(member.name):
                    return False
                
                # Check for '..' in the name
                if '..' in member.name:
                    return False
                
                # Resolve the member's path relative to the destination
                member_path = os.path.join(dest_path, member.name)
                resolved_member_path = os.path.realpath(member_path)
                
                # Ensure the resolved path is within the destination directory
                if not resolved_member_path.startswith(os.path.normpath(dest_path)):
                    return False
                
                # Check if the member is a symbolic link
                if member.issym() or member.islnk():
                    # Get the link target
                    link_target = member.linkname
                    
                    # Resolve the link target relative to the destination
                    if os.path.isabs(link_target):
                        # If absolute, check if it's within dest_path
                        resolved_link_target = os.path.realpath(link_target)
                        if not resolved_link_target.startswith(os.path.normpath(dest_path)):
                            return False
                    else:
                        # If relative, resolve it relative to the member's location
                        # But since we're validating before extraction, we need to be careful
                        # The safest approach is to resolve it relative to the destination
                        # However, the spec says "declared target points inside dest_path must be rejected"
                        # We need to resolve the link target relative to the member's location
                        # But we can't extract yet. So we check if the resolved path is outside dest_path
                        # Actually, for symlinks, we should check if the target resolves outside dest_path
                        # The target could be relative to the member's location
                        # Let's resolve it relative to the member's location (which is in dest_path)
                        member_dir = os.path.dirname(member_path)
                        resolved_link_target = os.path.realpath(os.path.join(member_dir, link_target))
                        if not resolved_link_target.startswith(os.path.normpath(dest_path)):
                            return False
                
                # Check if it's a hard link
                if member.islnk():
                    # Hard links are stored in the archive with the same name
                    # We need to check if the hard link target is valid
                    # The hard link target is stored in the linkname field
                    if not member.linkname:
                        continue
                    
                    # Check if the hard link target is within dest_path
                    if not member.linkname.startswith(os.path.normpath(dest_path)):
                        return False
                    
                    # Also check if the resolved path is within dest_path
                    resolved_link_target = os.path.realpath(member.linkname)
                    if not resolved_link_target.startswith(os.path.normpath(dest_path)):
                        return False
                
                # Check if the member is a device file or other special file
                if member.type == tarfile.S_IFREG:
                    pass
                elif member.type == tarfile.S_IFDIR:
                    pass
                else:
                    # For other types (devices, etc.), we should be cautious
                    # But the main concern is path traversal
                    pass
            
            # If validation passes, proceed with extraction
            for member in members:
                if member.isdir():
                    continue
                
                # Extract the member
                tar.extract(member, dest_path)
            
            return True
            
    except Exception:
        return False
