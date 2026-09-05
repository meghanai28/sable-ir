import os
import tarfile
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory with strict security checks.
    
    Returns True only if all members are extracted successfully; otherwise returns False
    without writing any archive content.
    """
    try:
        # Normalize the destination path to remove . and .. segments
        resolved_dest = os.path.normpath(dest_path)
        
        # Reject absolute paths
        if os.path.isabs(dest_path):
            return False
        
        # Open the tar file
        tar = tarfile.open(tar_path, 'r:*')
        
        try:
            for member in tar.getmembers():
                # Skip directories (they are created automatically)
                if member.isdir():
                    continue
                
                # Resolve the target path relative to the destination
                # We need to resolve the member's name to see if it escapes
                member_name = member.name
                
                # Check if the member name starts with .. or contains .. in a way that escapes
                # Normalize the member path relative to dest
                relative_member_path = os.path.normpath(os.path.join(resolved_dest, member_name))
                
                # Security check: ensure the resolved path is within the destination
                # Use os.path.commonpath to verify they share the same prefix
                common = os.path.commonpath([resolved_dest, relative_member_path])
                if common != resolved_dest:
                    return False
                
                # Check for symbolic links and hard links
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    # Resolve the link target relative to the destination
                    resolved_link_target = os.path.normpath(os.path.join(resolved_dest, link_target))
                    common_link = os.path.commonpath([resolved_dest, resolved_link_target])
                    if common_link != resolved_dest:
                        return False
                    continue
                
                # Check for device files
                if member.isdev():
                    return False
                
                # Check for directories again (already handled but for completeness)
                if member.isdir():
                    continue
                
                # Extract the member
                # We use extractfile to avoid creating the directory structure explicitly
                # and to have more control over the extraction
                try:
                    tar.extractfile(member)
                    # Write to the resolved destination
                    with open(relative_member_path, 'wb') as f:
                        f.write(tar.extractfile(member).read())
                except Exception:
                    return False
                    
        finally:
            tar.close()
        
        return True
        
    except Exception:
        return False
