import os
import tarfile
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory with strict path validation.
    
    Args:
        tar_path: Path to the tar archive.
        dest_path: Destination directory for extraction.
        
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    try:
        # Resolve and normalize the destination path
        dest_dir = os.path.realpath(dest_path)
        
        # Ensure the destination directory exists and is a directory
        if not os.path.isdir(dest_dir):
            return False
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            for member in tar.getmembers():
                # Skip directories that are not explicitly requested to be created,
                # but standard tar extraction creates them. We validate all members.
                
                # Calculate the target path within the destination
                target_path = os.path.join(dest_dir, member.name)
                
                # Normalize the target path to resolve any .. or . components
                # This prevents directory traversal via path manipulation
                normalized_target = os.path.normpath(target_path)
                
                # Resolve the real path to check for symlink escapes
                # We need to resolve the path as if it were created in the destination
                # to detect escapes from symlinks or hard links
                resolved_target = os.path.realpath(normalized_target)
                
                # Check if the resolved target is outside the destination directory
                if not resolved_target.startswith(dest_dir + os.sep) and resolved_target != dest_dir:
                    # This check handles the case where the destination is a file or the path is exactly the directory
                    # but we want to ensure we don't write outside.
                    # More robustly, we check if it's within the directory tree
                    if not (resolved_target == dest_dir or resolved_target.startswith(dest_dir + os.sep)):
                        return False
                
                # Handle symbolic links specifically
                if member.issym() or member.islnk():
                    # Get the link target
                    link_target = member.linkname
                    
                    # Normalize the link target
                    normalized_link_target = os.path.normpath(link_target)
                    
                    # Resolve the link target relative to the destination directory
                    # This simulates what would happen if the link were created
                    resolved_link_target = os.path.realpath(os.path.join(dest_dir, normalized_link_target))
                    
                    # Check if the resolved link target escapes the destination
                    if not (resolved_link_target == dest_dir or resolved_link_target.startswith(dest_dir + os.sep)):
                        return False
                    
                    # For symlinks, we don't create the file, but we might need to create the directory structure
                    # However, the requirement says "reject symbolic links... whose resolved target would escape"
                    # We must not extract the link itself if it escapes, but we can skip creating the symlink
                    # The member extraction will fail or we skip it.
                    # To be safe, we skip creating the symlink but ensure no directory is created that would be used for it
                    # Actually, standard behavior for unsafe symlinks is to skip extraction.
                    # But we must ensure no files are created.
                    # We will just skip this member extraction.
                    continue
                
                # Validate hard links
                if member.islnk():
                    # Hard links are handled similarly to symlinks in terms of target validation
                    # But hard links are stored within the archive, so the target is relative to the archive root
                    # We need to resolve the hard link target relative to the destination
                    # This is tricky because hard links in tar are stored with a name, not a path
                    # We treat the link name as a path relative to the destination
                    normalized_link_target = os.path.normpath(member.linkname)
                    resolved_link_target = os.path.realpath(os.path.join(dest_dir, normalized_link_target))
                    
                    if not (resolved_link_target == dest_dir or resolved_link_target.startswith(dest_dir + os.sep)):
                        return False
                
                # Attempt to extract the member
                try:
                    tar.extract(member, dest_dir, set_attrs=False)
                except (tarfile.TarError, OSError):
                    return False
            
            return True
            
    except Exception:
        return False
