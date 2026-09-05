import os
import tarfile
import shutil
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory, validating that no
    archive member (including symlinks and hard links) escapes the destination.
    
    Returns True on complete success, False on any validation or extraction failure.
    """
    try:
        # Normalize the destination path to an absolute path without trailing slashes
        # This ensures consistent comparison and prevents path traversal via ..
        dest_path = os.path.normpath(os.path.abspath(dest_path))
        
        # If the destination does not exist, create it
        if not os.path.exists(dest_path):
            os.makedirs(dest_path, exist_ok=True)
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Validate all members before extraction
            for member in tar.getmembers():
                # Get the raw name of the member (without directory traversal)
                raw_name = member.name
                
                # Skip . and .. components in the raw name
                while '..' in raw_name.split(os.sep):
                    raw_name = raw_name.replace(os.sep + '..' + os.sep, os.sep)
                if raw_name.endswith(os.sep + '..'):
                    raw_name = raw_name[:-len(os.sep + '..')]
                
                # Resolve the target path
                target_path = os.path.normpath(os.path.join(dest_path, raw_name))
                
                # Ensure the target is within the destination directory
                # Use os.path.commonpath to verify containment safely
                common_path = os.path.commonpath([dest_path, target_path])
                if not target_path.startswith(common_path + os.sep) and target_path != common_path:
                    raise ValueError(f"Member {member.name} would escape the destination directory")
                
                # For symlinks and hard links, resolve their targets and check containment
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    # Resolve the link target relative to the member's location
                    # If the member is a symlink, its location is the same as the archive member's name
                    # If it's a hard link, the location is the destination directory
                    if member.issym():
                        # Resolve the symlink target
                        resolved_link = os.path.normpath(os.path.join(dest_path, raw_name, link_target))
                    else:
                        resolved_link = os.path.normpath(os.path.join(dest_path, raw_name, link_target))
                    
                    # Ensure the resolved link target is within the destination
                    common_path = os.path.commonpath([dest_path, resolved_link])
                    if not resolved_link.startswith(common_path + os.sep) and resolved_link != common_path:
                        raise ValueError(f"Member {member.name} link target {link_target} would escape the destination directory")
            
            # If validation passes, extract the archive
            tar.extractall(path=dest_path)
            
            return True
            
    except Exception as e:
        return False
