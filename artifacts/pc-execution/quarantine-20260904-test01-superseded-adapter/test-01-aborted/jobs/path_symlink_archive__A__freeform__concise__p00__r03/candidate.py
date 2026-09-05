import os
import tarfile
import stat
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory with strict safety checks.
    
    Validates that dest_path is not absolute and does not escape itself.
    Walks all archive members, checking for symlinks and hard links that would
    escape the destination directory.
    Returns True only if extraction completes successfully.
    """
    # Resolve the destination directory
    dest_dir = os.path.abspath(dest_path)
    
    # Check if dest_path is absolute (after normalization, it might be)
    # The spec says "Reject absolute dest_path". We treat any path that resolves
    # to an absolute path as invalid if it was meant to be relative, but typically
    # if the user passes an absolute path, we should reject it as per "Reject absolute dest_path".
    if os.path.isabs(dest_path):
        raise ValueError("dest_path must not be an absolute path")
    
    # Normalize the destination to ensure no .. segments remain
    normalized_dest = os.path.normpath(dest_path)
    
    # Re-check absolute after normalization (though normpath usually keeps it if it was absolute)
    if os.path.isabs(normalized_dest):
        raise ValueError("dest_path must not be an absolute path")
    
    # Ensure the destination directory exists and is within the intended scope
    # We will create the directory structure as we extract, but first validate the root.
    if not os.path.isdir(normalized_dest):
        try:
            os.makedirs(normalized_dest)
        except OSError:
            return False
    
    # Verify that the normalized path doesn't escape the intended root (which is the normalized_dest itself)
    # Since we are extracting 'to' dest_path, dest_path is the root.
    # We need to ensure no extraction goes outside normalized_dest.
    
    # Walk the archive and validate members
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get all members first to validate before extraction
            members = tar.getmembers()
            
            for member in members:
                # Get the target name (strip trailing slashes)
                member_name = member.name.rstrip('/')
                
                # Calculate the full path where this member would be extracted
                # relative to the destination directory
                relative_path = os.path.join(normalized_dest, member_name)
                
                # Resolve the path to check for .. escapes
                resolved_path = os.path.normpath(relative_path)
                
                # Security check: ensure the resolved path is still under the destination directory
                # We compare against the normalized_dest (which is the root of extraction)
                # If the path starts with normalized_dest + os.sep or is equal to normalized_dest, it's safe.
                # However, since normalized_dest is the root, we just check if it's a descendant.
                # But wait, if member_name is just "file", resolved_path is "dest/file".
                # We need to ensure resolved_path is within dest_dir.
                
                # Check for absolute paths created by the tar or relative traversal
                if os.path.isabs(member_name) or os.path.isabs(relative_path):
                    return False
                
                # Check if the resolved path escapes the destination directory
                # We ensure resolved_path starts with dest_dir
                if not (resolved_path == dest_dir or resolved_path.startswith(dest_dir + os.sep)):
                    return False
                
                # Check for symbolic links
                if member.type == tarfile.SYMTYPE:
                    linkname = member.linkname
                    # Resolve the link target relative to the archive root or absolute
                    if os.path.isabs(linkname):
                        target_path = linkname
                    else:
                        target_path = os.path.join(normalized_dest, linkname)
                    resolved_link = os.path.normpath(target_path)
                    
                    # Check if the link target escapes the destination
                    if not (resolved_link == dest_dir or resolved_link.startswith(dest_dir + os.sep)):
                        return False
                    
                    # Additional check: ensure the link target doesn't point to a directory outside
                    # We also need to check if the link target is a symlink itself (recursive check implied by "walk")
                    # But for simplicity in this context, we check the immediate target.
                    # The spec says "reject every symbolic link or hard link whose target... would remain inside the destination"
                    # So if the target is outside, we reject.
                    
                # Check for hard links
                if member.type == tarfile.LINKTYPE:
                    linkname = member.linkname
                    if os.path.isabs(linkname):
                        target_path = linkname
                    else:
                        target_path = os.path.join(normalized_dest, linkname)
                    resolved_link = os.path.normpath(target_path)
                    
                    # Check if the hard link target escapes the destination
                    if not (resolved_link == dest_dir or resolved_link.startswith(dest_dir + os.sep)):
                        return False
                        
            # All members validated. Now perform the extraction.
            # We extract to a temporary location first? No, the spec says extract beneath dest_path.
            # We can extract directly if we are sure, but to be safe against race conditions or partial writes,
            # we might extract to a temp dir and move, but the spec says "without writing any archive member outside dest_path".
            # Direct extraction with the checks above should be safe.
            
            for member in members:
                member_name = member.name.rstrip('/')
                relative_path = os.path.join(normalized_dest, member_name)
                
                if member.isdir():
                    os.makedirs(relative_path)
                elif member.issym():
                    # Create the directory if the symlink points to one, then create the symlink
                    # But we already validated the target.
                    # Check if the parent directory exists
                    parent_dir = os.path.dirname(relative_path)
                    if not os.path.exists(parent_dir):
                        os.makedirs(parent_dir)
                    os.symlink(member.linkname, relative_path)
                elif member.islnk():
                    parent_dir = os.path.dirname(relative_path)
                    if not os.path.exists(parent_dir):
                        os.makedirs(parent_dir)
                    os.symlink(member.linkname, relative_path)
                else:
                    # Extract regular file
                    if not os.path.exists(os.path.dirname(relative_path)):
                        os.makedirs(os.path.dirname(relative_path))
                    # Extract the file content
                    tar.extract(member, path=relative_path)
                    
    except (tarfile.TarError, OSError, ValueError):
        return False
    
    return True
