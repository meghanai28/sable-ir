import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with security validation.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory for extraction.
        
    Returns:
        True if extraction completes successfully, False otherwise.
        No files are written outside dest_path on failure.
    """
    try:
        # Normalize and resolve the destination root
        dest_path = os.path.normpath(dest_path)
        dest_root = os.path.realpath(dest_path)
        
        # Ensure dest_path exists and is a directory
        if not os.path.isdir(dest_root):
            return False
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get the list of all members
            members = tar.getnames()
            
            # Validate each member before extraction
            for member in members:
                # Skip directories (they are handled by the extraction process, but we check files)
                # We need to check both regular files and directories to ensure they don't escape
                member_info = tar.getmember(member)
                
                # Check for symbolic links or hard links
                if member_info.issym() or member_info.islnk():
                    raise ValueError(f"Symbolic or hard link detected: {member}")
                
                # Resolve the target path
                member_dir = os.path.dirname(member)
                member_base = os.path.basename(member)
                
                # Construct the full path within the destination
                # For directories, we check if they would be created outside dest_root
                # For files, we check if they would be created outside dest_root
                
                # Calculate the relative path from dest_root
                if member_dir:
                    relative_path = os.path.join(member_dir, member_base)
                else:
                    relative_path = member_base
                
                # Resolve the target path relative to dest_root
                # We need to check if the resolved path escapes the destination root
                try:
                    resolved_member = os.path.normpath(os.path.join(dest_root, relative_path))
                except ValueError:
                    # This can happen if the path contains .. that goes outside
                    resolved_member = os.path.normpath(os.path.join(dest_root, relative_path))
                
                # Check if the resolved path is outside the destination root
                # We use os.path.commonpath to check if the path is within the destination
                try:
                    common = os.path.commonpath([dest_root, resolved_member])
                    if common != dest_root:
                        raise ValueError(f"Member path escapes destination: {member}")
                except ValueError:
                    # If commonpath fails, it means the paths are not on the same filesystem or something similar
                    raise ValueError(f"Invalid path structure: {member}")
            
            # Extract the archive
            tar.extractall(path=dest_root)
            
            return True
            
    except Exception as e:
        return False
