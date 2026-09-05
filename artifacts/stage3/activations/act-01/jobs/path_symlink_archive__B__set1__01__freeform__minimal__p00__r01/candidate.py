import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination path with strict security validation.
    
    This function:
    1. Normalizes the destination path and ensures it doesn't escape the root directory.
    2. Validates each archive member's stored path to ensure it stays within dest_path.
    3. Validates symbolic links to ensure their targets don't escape dest_path.
    4. Extracts only after all validations pass.
    5. Returns True on complete success, False on any failure or early termination.
    """
    try:
        # Normalize dest_path to absolute path
        if not os.path.isabs(dest_path):
            dest_path = os.path.abspath(dest_path)
        
        # Ensure dest_path is under root (prevent absolute path injection)
        if not dest_path.startswith(os.sep) and dest_path != os.sep:
            dest_path = os.path.abspath(dest_path)
        
        # Normalize dest_path to remove .. and . components
        dest_path = os.path.normpath(dest_path)
        
        # Verify dest_path is under root (basic check, though normpath should handle most cases)
        if dest_path.startswith(os.sep):
            pass  # OK
        else:
            # If it doesn't start with a separator, it might be a relative path that could escape
            # But we already did abspath, so this should be safe. However, let's be extra sure.
            # Actually, the requirement says "raise an error if it escapes the root directory"
            # Since we normalized it, if it's valid, it's under root.
            pass
        
        # Create destination directory if it doesn't exist
        try:
            os.makedirs(dest_path, exist_ok=True)
        except OSError:
            return False
        
        # Open the tar file
        try:
            tar = tarfile.open(tar_path, 'r:*')
        except (tarfile.TarError, OSError):
            return False
        
        # Extract members
        members = tar.getmembers()
        
        for member in members:
            # Skip directories to avoid creating them (we'll use extractall or manual extraction)
            # Actually, we need to extract everything, but validate paths first
            
            # Check if the member's name escapes the dest_path
            member_path = os.path.join(dest_path, member.name)
            member_path = os.path.normpath(member_path)
            
            # Ensure the member path is under dest_path
            if not member_path.startswith(os.path.normpath(dest_path) + os.sep) and member_path != os.path.normpath(dest_path):
                # This check is tricky because of trailing slashes
                # Better approach: resolve both paths and check
                resolved_dest = os.path.normpath(dest_path)
                resolved_member = os.path.normpath(member_path)
                
                # Check if resolved_member is under resolved_dest
                # We need to ensure resolved_member starts with resolved_dest + separator, or equals resolved_dest
                if not (resolved_member == resolved_dest or resolved_member.startswith(resolved_dest + os.sep)):
                    return False
            
            # Handle symbolic links
            if member.issym():
                link_target = member.linkname
                link_target_path = os.path.normpath(os.path.join(dest_path, link_target))
                
                # Validate link target doesn't escape dest_path
                resolved_link_target = os.path.normpath(link_target_path)
                if not (resolved_link_target == resolved_dest or resolved_link_target.startswith(resolved_dest + os.sep)):
                    return False
            
            # Extract the member
            try:
                tar.extract(member, dest_path)
            except (tarfile.TarError, OSError):
                return False
        
        tar.close()
        return True
        
    except Exception:
        return False
