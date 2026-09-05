import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with security validations.
    
    Returns True on complete success, False on any failure without writing outside dest_path.
    """
    # Normalize the destination path to absolute, resolving .. and .
    try:
        dest_path = os.path.normpath(os.path.abspath(dest_path))
    except (ValueError, OSError):
        return False
    
    # Resolve the tar file's directory to check for escapes
    tar_dir = os.path.dirname(os.path.abspath(tar_path))
    
    # Validate that tar_path itself doesn't escape the intended extraction root (if dest_path is meant to be the root)
    # However, per spec, we normalize dest_path and check if any member escapes it.
    # We must ensure the extraction target is safe.
    
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # First, gather all members to validate them before extraction
            members = tar.getmembers()
            
            # Normalize dest_path to absolute
            abs_dest = os.path.abspath(dest_path)
            
            for member in members:
                # Resolve the member's name relative to the archive root
                member_name = member.name
                
                # Check for path traversal in the member name itself
                if '..' in member_name.split('/'):
                    return False
                
                # Construct the full path where the member would be extracted
                # We use os.path.join to combine dest_path with the member name
                # But we must handle the case where member name is absolute (should be rejected)
                if os.path.isabs(member_name):
                    return False
                
                # Construct the full target path
                target_path = os.path.join(abs_dest, member_name)
                
                # Normalize the target path to resolve . and ..
                normalized_target = os.path.normpath(target_path)
                
                # Check if the normalized target escapes the destination
                if not normalized_target.startswith(abs_dest + os.sep) and normalized_target != abs_dest:
                    return False
                
                # Additional check for symbolic links and hard links
                if member.issym() or member.islnk():
                    # For symlinks and hardlinks, we must check the target
                    link_target = member.linkname
                    if os.path.isabs(link_target):
                        return False
                    
                    # Resolve the link target relative to the archive root if needed
                    # But tarfile.linkname is absolute or relative to cwd.
                    # We need to resolve it relative to the archive root or check if it points outside.
                    # Actually, the safest way is to resolve the link target relative to the member's location if it's relative,
                    # but tarfile doesn't provide the member's location in the archive.
                    # We assume link_target is relative to the current directory or absolute.
                    # If absolute, we check if it's outside dest_path.
                    if os.path.isabs(link_target):
                        if not link_target.startswith(abs_dest + os.sep) and link_target != abs_dest:
                            return False
                    else:
                        # Resolve relative to the current working directory? No, we should resolve relative to the archive root?
                        # Actually, the spec says "declared target points inside the destination".
                        # If it's relative, it's relative to the extraction point (dest_path).
                        resolved_link = os.path.normpath(os.path.join(abs_dest, link_target))
                        if not resolved_link.startswith(abs_dest + os.sep) and resolved_link != abs_dest:
                            return False
                
                # Check for hard links
                if member.islnk():
                    # Similar check for hard links
                    link_target = member.linkname
                    if os.path.isabs(link_target):
                        if not link_target.startswith(abs_dest + os.sep) and link_target != abs_dest:
                            return False
                    else:
                        resolved_link = os.path.normpath(os.path.join(abs_dest, link_target))
                        if not resolved_link.startswith(abs_dest + os.sep) and resolved_link != abs_dest:
                            return False
            
            # If all members are valid, proceed with extraction
            for member in members:
                if member.isdir():
                    os.makedirs(os.path.join(abs_dest, member.name), exist_ok=True)
                elif member.issym() or member.islnk():
                    # Reject symlinks and hardlinks as per plan
                    return False
                else:
                    # Extract regular file
                    if member.isfile():
                        # Ensure the directory exists
                        dir_path = os.path.dirname(os.path.join(abs_dest, member.name))
                        if not os.path.exists(dir_path):
                            os.makedirs(dir_path)
                        # Extract the file
                        with tar.extractfile(member) as src:
                            dest_file = os.path.join(abs_dest, member.name)
                            with open(dest_file, 'wb') as dest:
                                shutil.copyfileobj(src, dest)
            return True
            
    except (tarfile.TarError, OSError, IOError):
        return False
