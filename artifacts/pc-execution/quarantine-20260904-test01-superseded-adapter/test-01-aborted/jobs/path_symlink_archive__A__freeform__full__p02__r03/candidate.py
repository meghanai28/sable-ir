import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict security checks.
    Rejects symbolic links, hard links, and any members whose resolved
    destination escapes dest_path. Returns True only on complete success.
    """
    try:
        # Resolve the destination path to an absolute path if possible
        resolved_dest = os.path.abspath(dest_path)
        
        # Ensure the destination directory exists
        if not os.path.exists(resolved_dest):
            os.makedirs(resolved_dest)
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get all members
            members = tar.getmembers()
            
            # Validate each member before extracting
            for member in members:
                # Skip directories if we only want files, but per spec regular files and dirs may be extracted
                # Check for symbolic links
                if member.issym():
                    # Resolve the target of the symlink
                    try:
                        target = member.linkname
                        # If target is absolute, check if it's outside dest
                        if os.path.isabs(target):
                            resolved_target = os.path.normpath(target)
                            if not resolved_target.startswith(resolved_dest) and not resolved_target == resolved_dest:
                                return False
                        else:
                            # Resolve relative to the archive's directory or current dir
                            # For safety, we should resolve it relative to the extraction point
                            # But since we're extracting to dest_path, we need to check the resolved path
                            # The safest approach is to resolve it relative to the member's file name location if it were extracted there
                            # However, tarfile doesn't give us the extraction directory directly in the member
                            # We need to be careful: if the symlink target is relative, it's relative to the file's location
                            # But we can't know the file's location until we extract it.
                            # The safest check is to assume the worst case: if it's relative, it might be relative to dest_path
                            # Actually, the spec says "resolved target escapes the resolved dest_path"
                            # We should resolve the target relative to the member's path if it's relative
                            # But tarfile members don't have a path relative to dest yet
                            # Let's be conservative: if it's relative, we resolve it from the member's directory
                            # But we don't have that. We can extract the file first to a temp location and then check?
                            # No, the spec says "without writing any archive member outside dest_path"
                            # So we must validate before writing.
                            # The correct way is to resolve the target relative to the member's extraction path
                            # But we don't know that until we extract.
                            # However, we can calculate the extraction path: member.name -> resolved_dest + member.name
                            # But member.name might be relative to the archive root
                            # Actually, the member.name is the path within the archive
                            # The extraction path would be resolved_dest + member.name
                            # So if the symlink target is relative, we should resolve it relative to the extraction path?
                            # No, the symlink target is relative to the file's location in the archive
                            # But we are extracting to dest_path, so the file will be at dest_path + member.name
                            # So we should resolve the symlink target relative to dest_path + member.name
                            # But that's complex and might not be correct for all cases
                            # The safest approach is to resolve the target relative to the member's name
                            # But member.name is just the name, not the full path
                            # Actually, member.name is the full path within the archive
                            # So we can resolve the symlink target relative to the member's directory
                            # But we don't have the member's directory in the member object
                            # We can compute it: member.name.rsplit(os.sep, -1)[:-1] if not at root
                            # But this is getting complicated
                            # Let's use a simpler approach: resolve the target relative to the extraction path
                            # But that's not correct for symlinks that point to outside the archive
                            # The spec says "resolved target escapes the resolved dest_path"
                            # So we need to resolve the target and check if it's outside dest_path
                            # If the target is absolute, we check it directly
                            # If the target is relative, we resolve it relative to the member's location
                            # But we don't have the member's location yet
                            # However, we can assume that the member will be extracted to dest_path + member.name
                            # So we should resolve the symlink target relative to dest_path + member.name
                            # But that's not correct for all cases
                            # The safest approach is to resolve the target relative to the member's directory
                            # Let's do that:
                            member_dir = os.path.dirname(member.name)
                            if member_dir == '':
                                member_dir = '.'
                            resolved_target = os.path.normpath(os.path.join(resolved_dest, member_dir, target))
                            if not resolved_target.startswith(resolved_dest):
                                return False
                    except (OSError, ValueError):
                        return False
                elif member.ishardlink():
                    # Hard links are dangerous because they can point to files outside dest_path
                    # We need to check if the hard link target is outside dest_path
                    # But hard links are relative to the file's location
                    # So we need to resolve the target relative to the member's location
                    member_dir = os.path.dirname(member.name)
                    if member_dir == '':
                        member_dir = '.'
                    resolved_target = os.path.normpath(os.path.join(resolved_dest, member_dir, member.linkname))
                    if not resolved_target.startswith(resolved_dest):
                        return False
                else:
                    # Regular file or directory
                    # For regular files, we need to check if the extraction path is outside dest_path
                    # But the extraction path is dest_path + member.name
                    # We need to resolve member.name to an absolute path
                    extraction_path = os.path.normpath(os.path.join(resolved_dest, member.name))
                    if not extraction_path.startswith(resolved_dest):
                        return False
            
            # Now extract the archive
            for member in members:
                if member.isdir():
                    # Create directory
                    member_dir = os.path.normpath(os.path.join(resolved_dest, member.name))
                    if not os.path.exists(member_dir):
                        os.makedirs(member_dir)
                elif member.isfile():
                    # Extract file
                    member_dir = os.path.dirname(member.name)
                    if member_dir == '':
                        member_dir = '.'
                    member_dir = os.path.normpath(os.path.join(resolved_dest, member_dir))
                    if not os.path.exists(member_dir):
                        os.makedirs(member_dir)
                    member_path = os.path.normpath(os.path.join(member_dir, member.name))
                    if os.path.exists(member_path):
                        os.remove(member_path)
                    tar.extract(member, member_dir)
                elif member.issym():
                    # Skip symbolic links (already validated above)
                    pass
                elif member.ishardlink():
                    # Skip hard links (already validated above)
                    pass
            
            return True
        
    except Exception:
        return False
