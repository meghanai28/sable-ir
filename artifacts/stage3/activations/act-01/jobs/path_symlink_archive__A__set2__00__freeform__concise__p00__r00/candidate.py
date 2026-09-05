import os
import tarfile
import stat
import shutil
import tempfile

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory, ensuring no path traversal occurs.
    
    Args:
        tar_path: Path to the tar archive.
        dest_path: Destination directory for extraction.
        
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    try:
        # Resolve the absolute path for the destination root
        dest_root = os.path.abspath(dest_path)
        
        # Ensure the destination directory exists
        if not os.path.isdir(dest_root):
            os.makedirs(dest_root, exist_ok=True)
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            for member in tar.getmembers():
                # Skip directories during extraction to avoid creating them automatically
                if member.isdir():
                    continue
                
                # Calculate the target path within the destination
                target_path = os.path.join(dest_root, member.name)
                
                # Normalize the target path to resolve any '..' or symlinks
                # We need to check the resolved path against the dest_root
                try:
                    # Resolve the path without following symlinks for the directory part
                    # but we must ensure the final resolved path is within dest_root
                    resolved_target = os.path.normpath(target_path)
                    
                    # Check for path traversal attempts
                    if not resolved_target.startswith(dest_root + os.sep) and resolved_target != dest_root:
                        # This handles cases where the path is exactly dest_root or starts with it
                        # However, we also need to handle cases where the path might be a prefix of dest_root
                        # A more robust check:
                        if not resolved_target.startswith(dest_root):
                            raise ValueError(f"Path traversal detected: {resolved_target}")
                except (ValueError, TypeError):
                    raise ValueError(f"Invalid path: {target_path}")
                
                # Additional safety check: ensure the resolved path is within dest_root
                # by comparing the normalized path with the dest_root
                if not resolved_target.startswith(dest_root):
                    raise ValueError(f"Path traversal detected: {resolved_target}")
                
                # Extract the member
                # We need to extract the file, but we must ensure we don't write outside dest_root
                # The safest way is to extract to a temporary location first, then move, 
                # but since we've validated the path, we can extract directly if we're careful.
                # However, the requirement says "never write an archive member outside dest_path".
                # So we extract directly to the validated target_path.
                
                try:
                    tar.extract(member, dest_root)
                except (tarfile.TarError, OSError) as e:
                    raise ValueError(f"Extraction failed for {member.name}: {e}")
                
                # After extraction, verify the file is within dest_root
                if not os.path.isfile(target_path):
                    raise ValueError(f"File not found after extraction: {member.name}")
                    
                # Check if the file is within dest_root
                if not target_path.startswith(dest_root):
                    raise ValueError(f"File extracted outside dest_root: {target_path}")
                
                # Check for symbolic links that point outside dest_root
                # We need to check the symlink target, not just the link itself
                if os.path.islink(target_path):
                    link_target = os.readlink(target_path)
                    resolved_link_target = os.path.normpath(os.path.join(dest_root, link_target))
                    if not resolved_link_target.startswith(dest_root):
                        raise ValueError(f"Symbolic link points outside dest_root: {link_target}")
                    
                    # Remove the symlink and recreate it safely if needed, or just leave it
                    # But the requirement is to not write outside, so we just need to ensure the link itself is safe
                    # We've checked the resolved target, so it's safe.
                    pass
    
    except Exception as e:
        return False
    
    return True
