import os
import tarfile
import shutil
import tempfile

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict security controls.
    
    Returns True only if extraction completes successfully.
    Returns False if validation fails, if a symbolic or hard link is detected,
    or if any member would be extracted outside dest_path.
    """
    # Ensure dest_path exists and is a directory
    if not os.path.isdir(dest_path):
        return False
    
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # First pass: validate all members
            for member in tar.getnames():
                # Calculate the target path within dest_path
                # We use os.path.join to ensure the member name is resolved relative to dest_path
                # We must ensure no .. or absolute paths are used
                if member.startswith('/'):
                    # Absolute paths are not allowed
                    return False
                
                # Resolve the target path
                target_path = os.path.normpath(os.path.join(dest_path, member))
                
                # Check for path traversal attempts
                # The normpath should have resolved .., but we double-check
                if not target_path.startswith(dest_path):
                    return False
                
                # Check for symbolic links
                if member.endswith('->') or member.endswith('/'):
                    # This check is heuristic; better to rely on tarfile's getmembers
                    pass
                
                # We need to check the actual link type from getmembers
                # But we can't getmembers yet. We'll do a second pass or check here.
                # Actually, we can check the member's mode bits if we look at the archive structure,
                # but the safest way is to validate the full member object.
                # However, we must validate BEFORE opening the file.
                # Let's re-iterate logic: we need to check for symlinks/hardlinks.
                # tarfile.getmembers() gives us the info.
                pass
            
            # Second pass: detailed validation with getmembers
            for member in tar.getmembers():
                # Skip directories that are just prefixes (handled by normpath usually, but be safe)
                # Check for symbolic links
                if member.issym() or member.islnk():
                    return False
                
                # Check for hard links
                if member.islnk():
                    return False
                
                # Resolve the target path
                target_path = os.path.normpath(os.path.join(dest_path, member.name))
                
                # Ensure the target is within dest_path
                if not target_path.startswith(dest_path):
                    return False
                
                # Ensure no .. in the relative path (double check)
                # os.path.normpath handles .., but let's be explicit
                rel_path = os.path.relpath(target_path, dest_path)
                if '..' in rel_path:
                    return False
            
            # Second pass passed. Now extract.
            # We must extract to dest_path directly.
            # We need to ensure we don't extract to a parent directory.
            
            # Extract members
            for member in tar.getmembers():
                # Skip if it's a symlink or hardlink (already checked, but good for safety)
                if member.issym() or member.islnk():
                    return False
                
                # Resolve target path again for safety during extraction
                target_path = os.path.normpath(os.path.join(dest_path, member.name))
                
                # Check for path traversal during extraction
                if not target_path.startswith(dest_path):
                    return False
                
                # Extract the member
                # Use extractfile to avoid issues with directory extraction if not needed,
                # but for directories we want them created.
                # We need to handle the case where member is a directory vs file.
                
                if member.isdir():
                    # Create directory
                    os.makedirs(target_path, exist_ok=True)
                else:
                    # Extract file
                    # We must ensure the directory part exists
                    dir_part = os.path.dirname(target_path)
                    if dir_part and not os.path.exists(dir_part):
                        os.makedirs(dir_part, exist_ok=True)
                    
                    tar.extractfile(member).extract(target_path)
            
            return True
            
    except (tarfile.TarError, IOError, OSError) as e:
        return False
