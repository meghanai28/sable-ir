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
        # Resolve and normalize the destination path
        dest_path_resolved = os.path.realpath(dest_path)
        
        # Ensure dest_path exists and is a directory
        if not os.path.isdir(dest_path_resolved):
            return False
            
        # Open the tar file
        tar = tarfile.open(tar_path, 'r:*')
        
        try:
            for member in tar.getmembers():
                # Skip if the member name is absolute or contains ..
                member_name = member.name
                if member_name.startswith('/') or '..' in member_name:
                    return False
                
                # Resolve the target path relative to dest_path
                target_dir = os.path.join(dest_path_resolved, os.path.dirname(member_name))
                target_file = os.path.join(target_dir, os.path.basename(member_name))
                target_resolved = os.path.realpath(target_file)
                
                # Check if the resolved path is within dest_path
                if not target_resolved.startswith(dest_path_resolved + os.sep) and target_resolved != dest_path_resolved:
                    return False
                
                # Additional check for symlinks and hardlinks that point outside dest_path
                # We need to check the link target if it exists in the archive metadata
                # For symlinks, we check the linkname
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    # Resolve link target relative to dest_path
                    link_dir = os.path.join(dest_path_resolved, os.path.dirname(link_target))
                    link_resolved = os.path.realpath(os.path.join(link_dir, os.path.basename(link_target)))
                    if not link_resolved.startswith(dest_path_resolved + os.sep) and link_resolved != dest_path_resolved:
                        return False
                
                # Extract the member
                try:
                    tar.extract(member, dest_path_resolved)
                except (tarfile.ExtractError, Exception):
                    return False
                    
        finally:
            tar.close()
            
        return True
        
    except Exception:
        return False
