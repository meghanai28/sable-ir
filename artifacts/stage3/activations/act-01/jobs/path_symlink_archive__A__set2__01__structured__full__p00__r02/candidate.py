import os
import tarfile
import shutil
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory, validating that no
    archive member would escape the destination path. Returns True on success,
    False on any validation or extraction failure.
    """
    try:
        # Resolve and normalize the destination path to an absolute path
        # We use os.path.realpath to resolve symlinks and .. segments
        resolved_dest = os.path.realpath(dest_path)
        
        # Ensure the destination directory exists
        if not os.path.isdir(resolved_dest):
            os.makedirs(resolved_dest, exist_ok=True)
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            for member in tar.getmembers():
                # Resolve the member's name relative to the destination
                # We need to handle the case where the member's name is absolute
                # by resolving it relative to the destination if it's not already absolute
                if member.name.startswith('/'):
                    member_name = member.name[1:]  # Remove leading slash
                else:
                    member_name = member.name
                
                # Construct the full path where the member would be extracted
                full_member_path = os.path.join(resolved_dest, member_name)
                
                # Resolve the full member path to check for escape attempts
                resolved_member_path = os.path.realpath(full_member_path)
                
                # Check if the resolved member path is within the resolved destination
                # We use os.path.commonpath to ensure we're comparing the same path components
                try:
                    common_path = os.path.commonpath([resolved_dest, resolved_member_path])
                    if common_path != resolved_dest:
                        raise ValueError(f"Archive member would escape destination: {member.name}")
                except ValueError:
                    # This can happen if paths are on different drives (Windows) or have different root structures
                    raise ValueError(f"Archive member would escape destination: {member.name}")
                
                # Additional check for symlinks: ensure the symlink target is also within dest
                if member.issym() or member.islnk():
                    try:
                        link_target = member.linkname
                        resolved_link_target = os.path.realpath(os.path.join(resolved_dest, link_target))
                        common_link_path = os.path.commonpath([resolved_dest, resolved_link_target])
                        if common_link_path != resolved_dest:
                            raise ValueError(f"Symlink target would escape destination: {member.name} -> {link_target}")
                    except ValueError:
                        raise ValueError(f"Symlink target would escape destination: {member.name} -> {link_target}")
                
                # If all checks pass, add the member to the archive
                tar.extract(member, resolved_dest)
        
        return True
    
    except Exception as e:
        return False
