import tarfile
import os
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory, rejecting any symbolic links or hard links.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Directory where the archive should be extracted.
    
    Returns:
        True if extraction completes successfully with all members validated; False otherwise.
    """
    try:
        # Ensure dest_path exists and is a directory
        if not os.path.isdir(dest_path):
            return False
        
        with tarfile.open(tar_path, 'r:*') as tar:
            for member in tar.getmembers():
                # Skip directories that are not explicitly requested to be extracted (though tar usually extracts them)
                # We allow directories but reject symlinks and hardlinks
                
                # Check for symbolic links
                if member.issym() or member.islnk():
                    return False
                
                # Check for hard links
                if member.islnk() or member.linkname != '':
                    # islnk() is True if it's a hard link
                    return False
                
                # For regular files and directories, we need to ensure they stay within dest_path
                # Check if the target directory for the member is within dest_path
                target_dir = os.path.dirname(member.name)
                
                # Resolve the target path relative to dest_path to ensure it stays within
                if not target_dir.startswith(dest_path):
                    return False
                
                # Extract the member
                try:
                    tar.extract(member, dest_path)
                except Exception:
                    return False
            
            return True
    
    except Exception:
        return False
