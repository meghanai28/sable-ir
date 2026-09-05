import os
import tarfile
import shutil
import tempfile

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
        # Normalize paths to absolute forms
        tar_path = os.path.abspath(tar_path)
        dest_path = os.path.abspath(dest_path)
        
        # Validate destination path does not escape root
        if not dest_path.startswith(os.sep) and not dest_path == '.':
            # On Windows, check for drive letter; on Unix, check for root
            if os.name == 'nt':
                if not dest_path.startswith(('\\', '/')):
                    raise ValueError("Destination path must be absolute.")
            else:
                if not dest_path.startswith('/'):
                    raise ValueError("Destination path must be absolute.")
        
        # Ensure destination exists
        if not os.path.exists(dest_path):
            os.makedirs(dest_path, exist_ok=True)
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Validate archive members before extraction
            for member in tar.getmembers():
                # Resolve the full path for the member
                full_member_path = os.path.normpath(os.path.join(dest_path, member.name))
                
                # Check if the member name itself escapes dest_path
                if not full_member_path.startswith(dest_path):
                    raise ValueError(f"Archive member '{member.name}' escapes destination path.")
                
                # Follow symbolic links and hard links to check targets
                if member.issym() or member.islnk():
                    # For symlinks and links, check the target
                    target = member.linkname
                    # Resolve the target relative to the member's location
                    # The target is relative to the member's directory or the archive root
                    # We need to resolve it as if the member was extracted
                    # If the member is a symlink, the target is relative to the symlink's location
                    # If the member is a link, the target is relative to the link's location
                    
                    # Calculate the directory of the member
                    member_dir = os.path.dirname(full_member_path)
                    
                    # Resolve the target
                    resolved_target = os.path.normpath(os.path.join(member_dir, target))
                    
                    # Check if the resolved target escapes dest_path
                    if not resolved_target.startswith(dest_path):
                        raise ValueError(f"Symbolic/hard link target '{target}' in '{member.name}' escapes destination path.")
                    
                    # Additional check: if the target is a directory, ensure it's valid
                    # But we must also check if the target is outside dest_path
                    # The above check handles the main escape condition
                    
                elif member.isdir() or member.isfile():
                    # For regular files and directories, check the member path
                    # We already checked member.name above, but let's be thorough
                    if not full_member_path.startswith(dest_path):
                        raise ValueError(f"Archive member '{member.name}' escapes destination path.")
                    
                    # Check for .. in the member path
                    # This is covered by the normpath and startswith check, but explicit check for safety
                    parts = member.name.split(os.sep)
                    if '..' in parts:
                        raise ValueError(f"Archive member '{member.name}' contains '..' which could escape destination.")
            
            # Extract the archive
            for member in tar.getmembers():
                # Skip if validation would fail (though we did it above)
                full_member_path = os.path.normpath(os.path.join(dest_path, member.name))
                
                if not full_member_path.startswith(dest_path):
                    raise ValueError(f"Archive member '{member.name}' escapes destination path.")
                
                if member.isdir():
                    os.makedirs(full_member_path, exist_ok=True)
                else:
                    # Create parent directories
                    parent_dir = os.path.dirname(full_member_path)
                    if parent_dir and not os.path.exists(parent_dir):
                        os.makedirs(parent_dir, exist_ok=True)
                    
                    # Extract the file
                    if member.issym() or member.islnk():
                        # For symlinks and links, create the link
                        if member.issym():
                            os.symlink(member.linkname, full_member_path)
                        else:
                            os.symlink(member.linkname, full_member_path)
                    else:
                        # Extract regular file
                        with tar.extractfile(member) as src:
                            dest_file = open(full_member_path, 'wb')
                            shutil.copyfileobj(src, dest_file)
                            dest_file.close()
        
        return True
    
    except Exception as e:
        return False
