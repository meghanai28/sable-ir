import os
import tarfile
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict path validation.
    
    Returns True only if extraction completes successfully without writing outside dest_path.
    Returns False if validation fails or if any part of extraction fails.
    No archive members are written outside dest_path on failure.
    """
    try:
        # Normalize dest_path to absolute and resolve symlinks
        dest_path = os.path.realpath(dest_path)
        
        # Guard: Reject absolute paths that start with root
        if dest_path.startswith(os.sep) or dest_path == '/':
            return False
        
        # Ensure dest_path is not a symlink pointing outside root
        if os.path.islink(dest_path):
            return False
            
        # Create dest_path directory if it doesn't exist
        os.makedirs(dest_path, exist_ok=True)
        
        # Open the tar archive
        with tarfile.open(tar_path, 'r:*') as tar:
            # Guard: Walk each member and validate before extraction
            for member in tar.getmembers():
                # Resolve the full path for this member
                member_path = os.path.join(dest_path, member.name)
                
                # Normalize and resolve the member path
                resolved_member_path = os.path.realpath(member_path)
                
                # Guard: Check if the resolved path escapes the root
                if not resolved_member_path.startswith(dest_path):
                    return False
                
                # Guard: Check for absolute paths in member names
                if os.path.isabs(member.name):
                    return False
                
                # Guard: Check for .. in member path components
                if '..' in member.name.split(os.sep):
                    return False
                
                # Guard: Validate symbolic links
                if member.issym() or member.islnk():
                    # Resolve the link target
                    link_target = member.linkname
                    # Normalize the link target
                    normalized_link_target = os.path.normpath(link_target)
                    # Construct the full link target path
                    full_link_target = os.path.join(dest_path, normalized_link_target)
                    # Resolve the full link target
                    resolved_link_target = os.path.realpath(full_link_target)
                    # Guard: Check if the resolved link target escapes the root
                    if not resolved_link_target.startswith(dest_path):
                        return False
                    # Guard: Check if the link target itself is an absolute path
                    if os.path.isabs(link_target):
                        return False
                
                # Guard: Validate hard links
                if member.islnk():
                    link_target = member.linkname
                    normalized_link_target = os.path.normpath(link_target)
                    full_link_target = os.path.join(dest_path, normalized_link_target)
                    resolved_link_target = os.path.realpath(full_link_target)
                    if not resolved_link_target.startswith(dest_path):
                        return False
                    if os.path.isabs(link_target):
                        return False
                
                # Guard: Validate directory members
                if member.isdir():
                    if not member_path.endswith(os.sep):
                        member_path += os.sep
                    if not os.path.exists(member_path):
                        os.makedirs(member_path, exist_ok=True)
                
                # Guard: Validate regular files
                elif member.isfile():
                    if not os.path.exists(member_path):
                        with tar.extractfile(member) as src:
                            with open(member_path, 'wb') as dst:
                                dst.write(src.read())
            
            return True
            
    except Exception:
        return False
