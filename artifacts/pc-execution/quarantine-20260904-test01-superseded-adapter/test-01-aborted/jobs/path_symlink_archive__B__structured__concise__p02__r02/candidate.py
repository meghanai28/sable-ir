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
        True if extraction completes successfully and all members are within dest_path.
        False if validation or extraction fails, or if any member would escape dest_path.
    """
    try:
        # Normalize dest_path to absolute and resolve any .. segments
        dest_path = os.path.abspath(dest_path)
        
        # Guard: Reject absolute paths or paths that start with root (which abspath handles)
        # Ensure dest_path is not the root directory itself to prevent writing anywhere
        if dest_path == "/":
            raise ValueError("Destination cannot be the root directory")
        
        # Create dest_path if it doesn't exist
        os.makedirs(dest_path, exist_ok=True)
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Validate all members before extracting
            for member in tar.getmembers():
                # Get the target path relative to dest_path
                target_path = os.path.join(dest_path, member.name)
                
                # Normalize the target path to resolve .. and .
                normalized_target = os.path.normpath(target_path)
                
                # Guard: Ensure the normalized target is within dest_path
                # We check if the normalized target starts with dest_path
                if not (normalized_target == dest_path or normalized_target.startswith(dest_path + os.sep)):
                    raise ValueError(f"Path outside dest_path: {member.name}")
                
                # Guard: Reject symbolic links and hard links whose resolved target would leave dest_path
                # For symlinks, we need to resolve the link target
                if member.issym() or member.islnk():
                    # Resolve the link target
                    link_target = member.linkname
                    # Normalize the link target relative to the member's location
                    # The link target is relative to the member's directory
                    member_dir = os.path.dirname(member.name)
                    resolved_link_target = os.path.normpath(os.path.join(dest_path, member_dir, link_target))
                    
                    # Check if the resolved link target is within dest_path
                    if not (resolved_link_target == dest_path or resolved_link_target.startswith(dest_path + os.sep)):
                        raise ValueError(f"Symlink target outside dest_path: {member.name} -> {link_target}")
                
                # Guard: Reject hard links that would create a path outside dest_path
                # Hard links in tar are stored as (name, linkname)
                if member.isdir() or member.isfile():
                    # For directories, we just need to ensure the path is valid
                    # For files, we check the path
                    pass
                elif member.islnk():
                    # Hard links are handled similarly to symlinks in terms of path validation
                    # The linkname is relative to the target file's location
                    linkname = member.linkname
                    target_file_dir = os.path.dirname(member.name)
                    resolved_hard_link_target = os.path.normpath(os.path.join(dest_path, target_file_dir, linkname))
                    
                    if not (resolved_hard_link_target == dest_path or resolved_hard_link_target.startswith(dest_path + os.sep)):
                        raise ValueError(f"Hard link target outside dest_path: {member.name} -> {linkname}")
                
                # Extract the member
                tar.extract(member, dest_path)
            
            return True
            
    except Exception as e:
        return False
