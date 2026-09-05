import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination path with strict security validations.
    
    Args:
        tar_path: Path to the tar archive.
        dest_path: Destination directory for extraction.
    
    Returns:
        True if extraction completes successfully without writing outside dest_path.
        False if any validation or extraction fails.
    """
    try:
        # Normalize and validate dest_path to ensure it doesn't escape root
        dest_path = os.path.normpath(dest_path)
        if not dest_path.startswith(os.sep) and dest_path != os.sep:
            # Ensure dest_path is absolute or handle relative paths safely
            # If it's relative, we should still prevent escape, but the spec implies
            # treating inputs as potentially untrusted. We'll normalize to absolute
            # if possible, or ensure the base is safe.
            # A safe approach: resolve the real path of the destination directory.
            dest_path = os.path.abspath(dest_path)
        
        # Final check: ensure dest_path is within root (no .. escapes)
        if not dest_path.startswith(os.sep) and dest_path != os.sep:
            # If it's not absolute, we can't fully prevent escape without knowing the cwd,
            # but we will ensure we don't extract outside the resolved base.
            pass
        
        # Resolve the real path of the destination directory to prevent symlink escapes
        dest_dir = os.path.abspath(dest_path)
        
        # Check if dest_dir escapes root (though abspath usually prevents this,
        # we explicitly check for .. in the normalized form if we were doing relative)
        # The main safeguard is using os.path.abspath and ensuring we don't extract outside.
        # However, to be strict about "escapes the root directory", we check if the path
        # contains .. that could resolve to root.
        # Since we use abspath, we get the canonical path. We just need to ensure
        # the extraction doesn't go outside this canonical path.
        
        # Additional check: ensure dest_dir is not a symlink to something outside root
        # (Though abspath handles the path, we should be cautious)
        # We'll proceed with extraction but validate members strictly.
        
        # Validate dest_path is not a symlink to something outside root
        if os.path.islink(dest_path):
            raise ValueError("Destination path is a symbolic link")
        
        # Ensure dest_path exists and is a directory
        if not os.path.isdir(dest_path):
            os.makedirs(dest_path, exist_ok=True)
        
        # Open the tar archive
        with tarfile.open(tar_path, 'r:*') as tar:
            # Validate all members before extraction
            for member in tar.getmembers():
                # Calculate the target path for this member
                target_path = os.path.join(dest_path, member.name)
                
                # Normalize the target path to prevent .. escapes
                target_path = os.path.normpath(target_path)
                
                # Resolve the real path to check for symlink escapes
                target_real = os.path.realpath(target_path)
                
                # Check if the target path escapes the destination directory
                if not target_real.startswith(os.path.dirname(dest_path) + os.sep) and not target_real == os.path.dirname(dest_path):
                    raise ValueError(f"Extraction would escape destination directory: {target_path}")
                
                # Check for symbolic links
                if member.issym() or member.islnk():
                    raise ValueError(f"Symbolic link detected: {member.name}")
                
                # Check for hard links
                if member.islnk() or (member.isfile() and member.linkname):
                    # For hard links, check if the link name points outside dest
                    # The linkname is the target of the hard link
                    link_target = os.path.normpath(member.linkname)
                    link_real = os.path.realpath(os.path.join(dest_path, link_target))
                    if not link_real.startswith(os.path.dirname(dest_path) + os.sep) and not link_real == os.path.dirname(dest_path):
                        raise ValueError(f"Hard link target escapes destination: {member.name} -> {link_target}")
                
                # Check for device files
                if member.isdir() or member.isfile():
                    pass # Allow regular files and directories
                else:
                    # Skip device files or other non-standard types if strict
                    # But the spec says "raise an error if it is a symbolic link or a hard-link"
                    # It doesn't explicitly ban device files, but they are dangerous.
                    # We'll assume we only extract regular files and directories.
                    pass
            
            # Perform extraction
            tar.extractall(path=dest_path)
            
            return True
    
    except Exception:
        return False
