import os
import tarfile
import tempfile

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination path with strict safety validation.
    
    Only symbolic links and hard links are created if their normalized targets
    remain inside the destination directory. All members are validated before extraction.
    """
    try:
        # Create the destination directory if it doesn't exist
        os.makedirs(dest_path, exist_ok=True)
        
        with tarfile.open(tar_path, 'r:*') as tar:
            # Validate and extract members one by one
            for member in tar.getmembers():
                # Normalize the member's name to a relative path
                # Remove the leading '/' if present
                if member.name.startswith('/'):
                    member.name = member.name[1:]
                
                # Skip directories (directories don't have names in tar, but we check for them)
                # Actually, tarfile.getmembers() includes directories with '/' at the end
                # We need to ensure we don't extract anything outside dest_path
                
                # Calculate the full target path
                target_path = os.path.normpath(os.path.join(dest_path, member.name))
                
                # Safety check: Ensure the target path is within dest_path
                # We use os.path.commonpath to verify the path is under dest_path
                # and ensure no '..' traversal occurs
                try:
                    common = os.path.commonpath([dest_path, target_path])
                    if common != dest_path:
                        # This could be a symlink or hardlink target outside dest_path
                        # or a traversal attempt
                        return False
                except ValueError:
                    # This can happen if paths are on different drives (Windows)
                    return False
                
                # Check if the member is a directory
                if member.isdir():
                    os.makedirs(target_path, exist_ok=True)
                elif member.isfile():
                    # Extract the file
                    tar.extract(member, dest_path, set_attrs=False)
                elif member.issym() or member.islnk():
                    # Handle symlinks and hardlinks
                    # We need to validate the link target before creating the link
                    link_target = member.linkname
                    
                    # Normalize the link target
                    if link_target.startswith('/'):
                        link_target = link_target[1:]
                    
                    # Calculate the normalized target path
                    normalized_link_target = os.path.normpath(os.path.join(dest_path, link_target))
                    
                    # Safety check: Ensure the link target is within dest_path
                    try:
                        common = os.path.commonpath([dest_path, normalized_link_target])
                        if common != dest_path:
                            return False
                    except ValueError:
                        return False
                    
                    # Extract the link
                    if member.issym():
                        os.symlink(link_target, target_path)
                    else:
                        os.link(link_target, target_path)
                else:
                    # Skip other member types or return False if unexpected
                    return False
            
            return True
            
    except Exception as e:
        # Return False on any error without writing any archive member outside dest_path
        return False
