import os
import tarfile
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination path safely.
    
    Returns True only if the entire archive is successfully extracted without any
    validation or extraction failures. Returns False if any member would escape
    the destination, is a symlink/hardlink, or if extraction fails.
    """
    try:
        # Normalize and resolve the destination path to prevent directory traversal
        dest_path = os.path.normpath(dest_path)
        dest_dir = os.path.dirname(dest_path)
        if dest_dir:
            os.makedirs(dest_dir, exist_ok=True)
        
        # Resolve the destination to an absolute path to check for escapes
        resolved_dest = os.path.realpath(dest_path)
        
        with tarfile.open(tar_path, 'r:*') as tar:
            for member in tar.getmembers():
                # Skip directories to avoid creating them directly, we'll handle them via extraction
                # But we must validate their names
                
                # Check for symbolic links and hard links
                if member.issym() or member.islnk():
                    return False
                
                # Resolve the member's path relative to the destination
                # The member's name might contain .., so we must resolve it
                member_dir = os.path.dirname(member.name)
                member_base = os.path.basename(member.name)
                
                # Construct the full path where the member would be extracted
                # We need to ensure it stays within dest_path
                # Use realpath on the member's intended location to detect escapes
                # However, tarfile doesn't give the full path, just the name.
                # We construct the full path by joining dest_path with member.name
                # But we must be careful with .. in member.name
                
                # First, check if the member name itself escapes
                # We can do this by resolving the path relative to dest_path
                full_member_path = os.path.normpath(os.path.join(dest_path, member.name))
                resolved_member_path = os.path.realpath(full_member_path)
                
                # Check if the resolved path escapes the destination
                if not resolved_member_path.startswith(resolved_dest + os.sep) and resolved_member_path != resolved_dest:
                    return False
                
                # Check for symlinks/hardlinks pointing to outside or inside destination
                # The plan says: "raise if it is a symbolic link or hard link, even one that points inside the destination"
                # So we reject all symlinks and hardlinks regardless of target
                
                # Also, we must ensure that during extraction, we don't create files outside dest_path
                # The above check handles the name resolution.
                
                # Additional safety: check if the member name contains .. that could escape
                # os.path.normpath handles .., but we need to ensure the final path is within dest
                # The startswith check above should catch most cases, but let's be explicit
                
                # We also need to handle the case where the member is a directory
                # tarfile.extractfile will create the directory if needed, but we want to control it
                
                # Let's extract the member and catch any errors
                try:
                    tar.extract(member, path=dest_path)
                except Exception:
                    return False
                    
            return True
            
    except Exception:
        return False
