import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path, rejecting any symbolic or hard links.
    
    Args:
        tar_path: Path to the tar archive.
        dest_path: Destination directory for extraction.
        
    Returns:
        True if extraction completes successfully without violating safety rules,
        False otherwise. No files outside dest_path are written.
    """
    try:
        # Ensure dest_path exists and is a directory
        if not os.path.isdir(dest_path):
            return False
        
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get all members
            members = tar.getmembers()
            
            # Validate each member before extraction
            for member in members:
                # Resolve the destination path for this member
                # Use the member's name relative to dest_path
                dest_member = os.path.join(dest_path, member.name)
                
                # Check for .. components in the relative path
                # Normalize the path to resolve .. segments
                normalized_dest = os.path.normpath(dest_member)
                
                # Ensure the normalized path is still within dest_path
                # We check if the normalized path starts with dest_path (handling trailing slash)
                if not (normalized_dest == dest_path or normalized_dest.startswith(os.path.join(dest_path, os.sep))):
                    return False
                
                # Reject symbolic links and hard links
                if member.issym() or member.islnk():
                    return False
                
                # For directories, ensure no symlinks are created
                # (tarfile handles this, but we check the member type)
                if member.isdir():
                    if member.issym() or member.islnk():
                        return False
            
            # Extract the archive
            tar.extractall(path=dest_path)
            
            return True
            
    except Exception:
        return False
