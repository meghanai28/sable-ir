import os
import tarfile
import stat
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict path validation.
    
    Returns True only if extraction completes successfully.
    Returns False if any validation or extraction fails, ensuring no files
    are written outside dest_path.
    """
    try:
        # Normalize dest_path to an absolute path
        dest_path = os.path.normpath(os.path.abspath(dest_path))
        
        # Reject absolute dest_path that starts with .. or is not a valid directory
        if dest_path.startswith((".", "..")):
            return False
        
        # Ensure dest_path exists and is a directory
        if not os.path.isdir(dest_path):
            return False
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get the list of members
            members = tar.getmembers()
            
            # Validate all members before extracting any
            for member in members:
                # Resolve the member's name relative to dest_path
                member_name = member.name
                
                # Check for absolute paths or paths with ..
                if member_name.startswith(("/", "..")):
                    return False
                
                # Construct the full path for the member
                full_path = os.path.normpath(os.path.join(dest_path, member_name))
                
                # If the member is a directory, check if it's inside dest_path
                if member.isdir:
                    if not full_path.startswith(dest_path + os.sep) and full_path != dest_path:
                        return False
                # If the member is a file, check if it's inside dest_path
                elif member.isfile:
                    if not full_path.startswith(dest_path + os.sep) and full_path != dest_path:
                        return False
                # For symlinks, hardlinks, etc., we need to check the target
                elif member.issym or member.islnk:
                    # Check if the link target is inside dest_path
                    link_target = member.linkname
                    if not link_target.startswith((".", "..")):
                        # Resolve the link target relative to dest_path
                        resolved_target = os.path.normpath(os.path.join(dest_path, link_target))
                        if not resolved_target.startswith(dest_path + os.sep) and resolved_target != dest_path:
                            return False
                    else:
                        # If the link target contains .., reject it
                        return False
                else:
                    # For other types, check if the member name is safe
                    if not member_name.startswith((".", "..")):
                        full_path = os.path.normpath(os.path.join(dest_path, member_name))
                        if not full_path.startswith(dest_path + os.sep) and full_path != dest_path:
                            return False
            
            # If all validations pass, extract the archive
            for member in members:
                # Extract the member
                if member.isdir:
                    member.dir_name = dest_path + os.sep + member.name
                    member.external_attr = member.external_attr if member.external_attr else 0
                    member.external_attr = member.external_attr | stat.S_IFDIR
                    tar.extract(member, dest_path)
                else:
                    tar.extract(member, dest_path)
            
            return True
            
    except Exception:
        return False
