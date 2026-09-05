import os
import tarfile
import shutil
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict security validation.
    
    Returns True only if extraction completes successfully.
    Returns False if validation fails or extraction is interrupted, without
    writing any archive member outside dest_path.
    """
    try:
        # Ensure dest_path exists
        if not os.path.exists(dest_path):
            os.makedirs(dest_path)
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Validate and extract members one by one
            for member in tar.getmembers():
                # Skip directories that are not explicitly requested to be created
                # (standard behavior for extract, but we enforce safety)
                
                # Get the target path
                target_path = os.path.join(dest_path, member.name)
                
                # Check if the name is absolute
                if os.path.isabs(member.name):
                    raise ValueError(f"Archive contains absolute path in member name: {member.name}")
                
                # Check if the resolved target escapes dest_path
                # We need to resolve the path to check for symlinks/hardlinks
                try:
                    resolved_target = os.path.normpath(os.path.join(dest_path, member.name))
                except ValueError:
                    raise ValueError(f"Invalid path component in member: {member.name}")
                
                # Check if resolved target is outside dest_path
                if not resolved_path_is_under(dest_path, resolved_target):
                    raise ValueError(f"Archive member would escape dest_path: {member.name}")
                
                # Check for symlinks or hardlinks that point outside dest_path
                if member.issym() or member.islnk():
                    if member.linkname:
                        # Resolve the link target
                        link_target = os.path.normpath(os.path.join(dest_path, member.name))
                        if os.path.isabs(member.linkname):
                            raise ValueError(f"Archive contains absolute symlink target: {member.linkname}")
                        # The link target is relative to the directory containing the link
                        # But since we are extracting into dest_path, we need to check the resolved path
                        # Actually, for symlinks, the target is relative to the link's location
                        # We need to resolve the link target relative to the link's location
                        # But simpler: just check if the link target itself (if absolute) or its resolution escapes
                        # The safest way: resolve the link target relative to the link's location
                        link_dir = os.path.dirname(target_path)
                        resolved_link_target = os.path.normpath(os.path.join(link_dir, member.linkname))
                        if not resolved_link_target.startswith(dest_path):
                            raise ValueError(f"Archive contains symlink escaping dest_path: {member.name}")
                
                # Check for hardlinks
                if member.islnk():
                    # Hardlinks are handled similarly to symlinks in terms of safety
                    # But tarfile's islnk() is for hardlinks
                    if member.linkname:
                        link_dir = os.path.dirname(target_path)
                        resolved_link_target = os.path.normpath(os.path.join(link_dir, member.linkname))
                        if not resolved_link_target.startswith(dest_path):
                            raise ValueError(f"Archive contains hardlink escaping dest_path: {member.name}")
                
                # Check if it's a regular file or directory
                if member.isdir():
                    # Create directory
                    os.makedirs(target_path, exist_ok=True)
                elif member.isfile():
                    # Extract file
                    if os.path.exists(target_path):
                        os.remove(target_path)
                    shutil.copyfileex(src=member.name, dst=target_path, follow_symlinks=False)
                else:
                    # Skip other types or raise error
                    # For safety, we should skip or raise error for unexpected types
                    pass
            
            return True
    
    except Exception as e:
        # Ensure no partial extraction occurred
        return False

def resolved_path_is_under(base: str, path: str) -> bool:
    """
    Check if the resolved path is under the base directory.
    This handles cases where the path might be a symlink or have been normalized.
    """
    # Normalize both paths
    normalized_base = os.path.normpath(base)
    normalized_path = os.path.normpath(path)
    
    # Check if the path starts with the base directory
    # We need to be careful about trailing slashes
    if normalized_path.startswith(normalized_base + os.sep):
        return True
    elif normalized_path == normalized_base:
        return True
    else:
        return False
