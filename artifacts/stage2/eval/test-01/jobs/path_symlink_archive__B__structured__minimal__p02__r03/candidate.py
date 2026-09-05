import os
import tarfile
import stat

def _is_within_directory(path: str, directory: str) -> bool:
    """Check if path is within directory, handling .. and absolute paths."""
    try:
        abs_path = os.path.abspath(path)
        abs_dir = os.path.abspath(directory)
        # Ensure directory ends with separator for correct prefix check
        if not abs_dir.endswith(os.sep):
            abs_dir += os.sep
        return abs_path.startswith(abs_dir)
    except (ValueError, OSError):
        return False

def _validate_member(member: tarfile.TarInfo, dest_path: str) -> bool:
    """
    Validate that a tar member, when extracted to dest_path, does not escape.
    Returns True if safe, False otherwise.
    """
    try:
        if member.isdir():
            # For directories, we just check the name doesn't escape
            # We don't need to check the full path for the directory itself,
            # but we must ensure the parent directory doesn't escape.
            # The standard approach is to check if the member name resolves outside.
            # However, a safer check is to ensure the resolved path is within dest_path.
            # We resolve the member name relative to dest_path.
            member_path = os.path.join(dest_path, member.name)
            # Normalize to handle ..
            normalized = os.path.normpath(member_path)
            if not _is_within_directory(normalized, dest_path):
                return False
        else:
            # For files, we need to be more careful.
            # If it's a file, we check if the resolved path is within dest_path.
            # We also need to handle symlinks/hardlinks that might point outside.
            # But the spec says: "a symbolic-link or hard-link whose target would point inside dest_path is allowed"
            # Wait, the spec says: "raise an error unless each member's resolved destination remains inside dest_path"
            # AND "a symbolic-link or hard-link whose target would point inside dest_path is allowed only when its normalized target stays inside dest_path"
            # This implies we check the target of the link.
            # If it's a regular file, we assume the content is what matters, but the path must be safe.
            # Actually, the safest interpretation for "resolved destination" for a file is the file's own location.
            # But if it's a symlink, we must check the target.
            # Let's check the file's location first.
            member_path = os.path.join(dest_path, member.name)
            normalized = os.path.normpath(member_path)
            if not _is_within_directory(normalized, dest_path):
                return False
            
            # If it's a symlink, we must also check the target.
            # However, we cannot resolve the target until we know the file exists?
            # No, we can read the link path from the tar info.
            if member.issym() or member.islnk():
                link_target = member.linkname
                # Resolve the link target relative to the link location (which is inside dest_path)
                # If the link is absolute, it might escape.
                # If relative, resolve relative to the directory containing the link.
                link_dir = os.path.dirname(member_path)
                resolved_target = os.path.normpath(os.path.join(link_dir, link_target))
                if not _is_within_directory(resolved_target, dest_path):
                    return False
    except (ValueError, OSError):
        return False
    return True

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path, ensuring no path escapes.
    Returns True on success, False on failure.
    """
    try:
        # Normalize dest_path
        abs_dest = os.path.abspath(dest_path)
        if not os.path.isdir(abs_dest):
            # Create directory if it doesn't exist? The prompt says "extract beneath".
            # Usually implies the directory should exist or be created.
            # But the safety guard says "raise an error if it escapes".
            # If it doesn't exist, we might need to create it, but we must be careful.
            # Let's assume we create the directory structure if needed, but validate paths.
            pass
        
        # Validate dest_path is safe (no .. escapes if absolute, etc)
        # If dest_path is relative, we resolve it. If it contains .., it might escape.
        # We treat the resolved absolute path as the base.
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get list of members
            members = tar.getmembers()
            
            # Validate all members before extracting
            for member in members:
                if not _validate_member(member, abs_dest):
                    return False
            
            # Extract members
            for member in members:
                # We need to extract carefully.
                # If it's a directory, create it.
                # If it's a file, extract it.
                # We must ensure we don't write outside.
                # The _validate_member checked the path.
                # Now we extract.
                
                # Use extractfile or extract for safety
                # extractfile is safer as it doesn't follow symlinks unless specified, 
                # but we already validated the link target if it's a symlink.
                # However, tarfile.extract() has a 'onlink' parameter.
                # We should use 'onlink'='error' or 'onlink'='warn' or 'onlink'='copy' to be safe?
                # The spec says "a symbolic-link ... is allowed only when its normalized target stays inside dest_path".
                # We already checked that. So we can proceed.
                # But we must ensure we don't overwrite existing files outside dest_path.
                # Since we validated the path, it's inside.
                
                # Extracting to the resolved path
                # We need to make sure the parent directory exists.
                if member.isdir():
                    os.makedirs(os.path.join(abs_dest, member.name), exist_ok=True)
                else:
                    # Extract file
                    # We use extractfile to be safe about the path
                    # But extractfile might create parent dirs.
                    # Let's use extract with the specific file path.
                    # We need to ensure the parent dir exists.
                    parent_dir = os.path.dirname(os.path.join(abs_dest, member.name))
                    os.makedirs(parent_dir, exist_ok=True)
                    
                    # Extract the file
                    # We can use tar.extractfile(member) to get the file object
                    with tar.extractfile(member) as src:
                        # Write to destination
                        dest_file_path = os.path.join(abs_dest, member.name)
                        # Ensure parent exists (already done above for files)
                        # But if the file is a symlink, we might need to handle it differently?
                        # If it's a symlink, we create the link.
                        if member.issym() or member.islnk():
                            # Create symlink
                            # Check if target exists? No, just create link.
                            # But we must ensure the link target is valid.
                            # We already validated the link target.
                            os.symlink(member.linkname, dest_file_path)
                        else:
                            # Copy content
                            # Use shutil.copyfileobj or write directly
                            with open(dest_file_path, 'wb') as dst:
                                shutil.copyfileobj(src, dst)
                    
                    # If it was a hardlink, we need to handle it.
                    # tarfile handles hardlinks if we use the right method, but we are extracting manually.
                    # If it's a hardlink, member.linkname is the target.
                    # We should remove the file and create a hardlink?
                    # Or just let the tarfile handle it?
                    # The tarfile module has 'hardlinks' option.
                    # But we are doing manual extraction to be safe.
                    # If it's a hardlink, we should create the hardlink.
                    if member.islnk():
                        # Remove the file we just created (if any) and create hardlink
                        if os.path.exists(dest_file_path):
                            os.remove(dest_file_path)
                        os.link(member.linkname, dest_file_path)
                    
    except Exception:
        return False
    
    return True
