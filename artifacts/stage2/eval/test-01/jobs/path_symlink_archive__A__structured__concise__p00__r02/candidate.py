import os
import tarfile
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict security checks.
    
    Returns True only if extraction completes successfully without any
    side effects outside dest_path. Returns False on any validation or
    extraction failure, ensuring no archive members were written outside
    dest_path.
    """
    try:
        # Normalize dest_path to absolute and resolve .. segments
        dest_path = os.path.abspath(dest_path)
        
        # Ensure dest_path directory exists
        os.makedirs(dest_path, exist_ok=True)
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Validate all members before extraction
            for member in tar.getmembers():
                # Get the absolute path of the member's destination
                member_path = os.path.abspath(os.path.join(dest_path, member.name))
                
                # Check for path traversal
                if not member_path.startswith(dest_path):
                    return False
                
                # Check for symbolic links or hard links
                if member.issym() or member.islnk():
                    return False
                
                # Check for device files or other non-regular/non-directory types
                if member.isdir():
                    continue
                if member.isfile():
                    continue
                # Skip other types like directories if they were already handled above
                # But we must ensure we don't extract directories that escape
                # The above check handles the name path, but we also need to check
                # if the member is a directory that we are about to create.
                # Actually, the logic above is: if it's a dir, we skip the link check,
                # but we still need to ensure the name doesn't escape.
                # We already checked member_path.startswith(dest_path) above.
                # However, we must also ensure we don't create a directory that escapes.
                # Since we check member_path.startswith(dest_path) for all members,
                # and we only extract if it passes, we are safe.
                # But we need to be careful: if member.name is "../foo", member_path will be outside.
                # So the check above is sufficient.
                
                # Additional check: ensure the member is not a symlink or hardlink
                # even if it points outside. The plan says "even one that points inside the destination".
                # So we reject any symlink or hardlink.
                
                # Check for symbolic links or hard links
                if member.issym() or member.islnk():
                    return False
                
                # Check for device files or other non-regular/non-directory types
                # We only want regular files and directories.
                if not (member.isdir() or member.isfile()):
                    return False
            
            # If all members are valid, proceed with extraction
            for member in tar:
                if not member.isfile() and not member.isdir():
                    continue
                
                # Extract the member
                tar.extract(member, dest_path, set_attrs=False)
            
            return True
            
    except Exception:
        return False
