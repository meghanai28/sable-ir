import os
import tarfile
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to the specified destination path, ensuring no members
    escape the destination directory. Returns True on complete success, False otherwise.
    """
    try:
        # Resolve the destination path to an absolute path and normalize it
        # This ensures we work with a consistent, safe base directory
        resolved_dest = os.path.realpath(dest_path)
        
        # Ensure the destination directory exists
        if not os.path.exists(resolved_dest):
            os.makedirs(resolved_dest)
        
        # Open the tar archive
        with tarfile.open(tar_path, 'r:*') as tar:
            # List all members to be extracted
            members = tar.getnames()
            
            # Validate all members before extraction
            for member in members:
                # Resolve the member's target relative to the destination
                # We need to handle both regular files and symlinks/hardlinks
                # The member name itself might contain path separators
                member_path = os.path.join(resolved_dest, member)
                
                # Normalize the member path to check for escape attempts
                # We use realpath on the member path to resolve symlinks and ..
                # However, we must be careful not to resolve symlinks that are meant to be preserved
                # For tarfile, we need to check the target of symlinks and hardlinks
                normalized_member = os.path.normpath(member_path)
                
                # Check if the normalized path escapes the resolved destination
                if not normalized_member.startswith(resolved_dest + os.sep) and normalized_member != resolved_dest:
                    # This check handles the case where the path is exactly the dest or a child
                    # We also need to handle the case where the path is a child
                    if not normalized_member.startswith(resolved_dest):
                        raise ValueError(f"Member {member} would escape the destination directory")
                
                # Additional check for symlinks and hardlinks
                # We need to check the target of the member if it's a symlink or hardlink
                # tarfile.getmember() returns a TarInfo object
                if member in tar.getnames():
                    member_info = tar.getmember(member)
                    if member_info.issym() or member_info.islnk():
                        # Check the target of the symlink or hardlink
                        target = member_info.linkname
                        target_path = os.path.normpath(os.path.join(resolved_dest, member, target))
                        if not target_path.startswith(resolved_dest):
                            raise ValueError(f"Member {member} symlink/hardlink target {target} would escape the destination")
            
            # Extract the archive with error handling
            tar.extractall(path=resolved_dest)
            
            return True
            
    except Exception as e:
        return False
