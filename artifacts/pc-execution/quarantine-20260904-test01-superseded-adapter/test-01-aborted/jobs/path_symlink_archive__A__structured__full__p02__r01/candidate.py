import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path, rejecting any symbolic or hard links.
    Returns True only if extraction completes successfully without writing outside dest_path.
    """
    try:
        # Ensure dest_path exists and is a directory
        if not os.path.isdir(dest_path):
            os.makedirs(dest_path)
        else:
            os.makedirs(os.path.dirname(dest_path) if os.path.dirname(dest_path) else '.', exist_ok=True)
            os.chdir(dest_path)

        with tarfile.open(tar_path, 'r:*') as tar:
            # Collect all members and validate them first
            members = tar.getmembers()
            
            for member in members:
                # Skip directories if we want to be strict, but plan says dirs may be extracted
                # Check for symbolic links
                if member.issym() or member.islnk():
                    return False
                
                # Resolve the member's destination path relative to dest_path
                # We need to check if the target is within dest_path
                dest_member = os.path.join(dest_path, member.name)
                
                # If the member is a symlink, we already rejected it above
                # If the member is a hard link, we also reject it
                # For regular files and directories, we need to ensure the target is within dest_path
                # However, for regular files/dirs, the "target" is the file/dir itself, so we just check the path
                if os.path.dirname(dest_member) not in [dest_path] + [os.path.join(dest_path, '..')]:
                    # This check is tricky because dest_path might have trailing slashes or not
                    # Better approach: normalize paths
                    dest_member_norm = os.path.normpath(dest_member)
                    dest_path_norm = os.path.normpath(dest_path)
                    
                    if not dest_member_norm.startswith(dest_path_norm + os.sep) and dest_member_norm != dest_path_norm:
                        return False
            
            # Now perform the extraction
            for member in members:
                if member.isdir():
                    os.makedirs(os.path.join(dest_path, member.name))
                elif member.isfile():
                    os.makedirs(os.path.dirname(os.path.join(dest_path, member.name)), exist_ok=True)
                    shutil.copyfileobj(tar.extractfile(member), open(os.path.join(dest_path, member.name), 'wb'))
                else:
                    # Skip other types or handle as needed
                    pass
            
            return True
            
    except Exception:
        return False
