import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination path with safety validations.
    
    Validates that all archive members (including symlinks and hardlinks) are
    located within the destination directory before extraction. Returns True
    only if extraction completes successfully, otherwise False.
    """
    try:
        if not os.path.isdir(dest_path):
            os.makedirs(dest_path, exist_ok=True)
        
        with tarfile.open(tar_path, 'r:*') as tar:
            for member in tar.getmembers():
                # Resolve the member's path relative to dest_path
                # We need to check if the member's name (without leading /)
                # would resolve outside dest_path
                
                # Get the full path the member would have if extracted
                full_member_path = os.path.join(dest_path, member.name)
                
                # Normalize paths to resolve .. and . safely
                # We check if the normalized path is still within dest_path
                normalized_member = os.path.normpath(full_member_path)
                
                # Ensure the path doesn't escape the destination directory
                # by checking if the normalized path starts with the dest_path
                # (handling cases where dest_path might have trailing slashes or not)
                dest_normalized = os.path.normpath(dest_path)
                
                if not (normalized_member.startswith(dest_normalized + os.sep) or 
                        (normalized_member == dest_normalized and member.name == '')):
                    return False
                
                # Additional check for symlinks and hardlinks
                if member.issym() or member.islnk():
                    # For symlinks, ensure the target is also within dest_path
                    link_target = member.linkname
                    # Normalize the target path relative to the archive's root
                    # but we must ensure it doesn't point outside the archive's extraction root
                    # Actually, the policy says "normalized link target remains inside the destination"
                    # We need to resolve the link target relative to the member's location
                    if member.issym():
                        # Resolve the symlink target
                        link_target_path = os.path.normpath(os.path.join(os.path.dirname(full_member_path), link_target))
                        if not (link_target_path.startswith(dest_normalized + os.sep) or 
                                (link_target_path == dest_normalized and member.name == '')):
                            return False
                    elif member.islnk():
                        # Hardlinks are tricky; we can't extract them without knowing the source
                        # The policy says validate link target. For hardlinks in tar, the target is usually another member name.
                        # We should ensure the target member also passes validation
                        if member.linkname != '':
                            # Check if the target member is valid
                            if not (member.linkname.startswith(os.sep) or 
                                    os.path.normpath(os.path.join(dest_path, member.linkname)).startswith(dest_normalized + os.sep)):
                                return False
                
                # Extract the member
                tar.extract(member, dest_path)
        
        return True
        
    except Exception:
        return False
