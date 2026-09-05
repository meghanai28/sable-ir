import os
import tarfile
import stat
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory with strict security validation.
    
    This function:
    1. Validates that dest_path is not absolute and normalizes it.
    2. Ensures no extraction would escape the normalized dest_path by checking all archive entries.
    3. Walks through all archive members, following symbolic links and hard links, and rejects any that would resolve outside the destination.
    4. Performs all validation before extracting any part of the archive.
    5. Returns True only if the archive is fully extracted under dest_path, otherwise False.
    """
    # Normalize dest_path to ensure no path traversal
    dest_path = os.path.normpath(dest_path)
    
    # Reject absolute paths
    if os.path.isabs(dest_path):
        raise ValueError("dest_path must be a relative path")
    
    # Resolve the absolute path for comparison
    resolved_dest = os.path.abspath(dest_path)
    
    # Create the destination directory if it doesn't exist
    os.makedirs(resolved_dest, exist_ok=True)
    
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Validate all members before extraction
            for member in tar.getmembers():
                # Skip directories to avoid creating them during validation
                if member.isdir():
                    continue
                
                # Calculate the target path
                target_path = os.path.join(resolved_dest, member.name)
                
                # Normalize the target path to check for path traversal
                normalized_target = os.path.normpath(target_path)
                
                # Check if the normalized target escapes the destination
                if not normalized_target.startswith(resolved_dest + os.sep) and normalized_target != resolved_dest:
                    raise ValueError(f"Path traversal detected: {member.name}")
                
                # Check for symbolic links
                if member.issym() or member.islnk():
                    # Get the link target
                    link_target = member.linkname if member.islnk() else member.linkname
                    
                    # Normalize the link target
                    normalized_link_target = os.path.normpath(link_target)
                    
                    # Check if the link target resolves outside the destination
                    # We need to resolve the link target relative to the member's directory
                    member_dir = os.path.dirname(member.name)
                    resolved_link_target = os.path.normpath(os.path.join(resolved_dest, member_dir, normalized_link_target))
                    
                    if not resolved_link_target.startswith(resolved_dest + os.sep) and resolved_link_target != resolved_dest:
                        raise ValueError(f"Symbolic link would escape destination: {member.name} -> {link_target}")
                    
                    # Additional check: if the link target is absolute, it must be within dest
                    if os.path.isabs(link_target):
                        resolved_absolute_link = os.path.normpath(link_target)
                        if not resolved_absolute_link.startswith(resolved_dest + os.sep) and resolved_absolute_link != resolved_dest:
                            raise ValueError(f"Absolute symbolic link escapes destination: {member.name} -> {link_target}")
                
                # Check for hard links
                if member.islnk():
                    hard_link_target = member.linkname
                    # Normalize the hard link target
                    normalized_hard_link_target = os.path.normpath(hard_link_target)
                    
                    # Check if the hard link target resolves outside the destination
                    member_dir = os.path.dirname(member.name)
                    resolved_hard_link_target = os.path.normpath(os.path.join(resolved_dest, member_dir, normalized_hard_link_target))
                    
                    if not resolved_hard_link_target.startswith(resolved_dest + os.sep) and resolved_hard_link_target != resolved_dest:
                        raise ValueError(f"Hard link would escape destination: {member.name} -> {hard_link_target}")
                    
                    # Additional check: if the hard link target is absolute, it must be within dest
                    if os.path.isabs(hard_link_target):
                        resolved_absolute_hard_link = os.path.normpath(hard_link_target)
                        if not resolved_absolute_hard_link.startswith(resolved_dest + os.sep) and resolved_absolute_hard_link != resolved_dest:
                            raise ValueError(f"Absolute hard link escapes destination: {member.name} -> {hard_link_target}")
            
            # If validation passes, extract the archive
            tar.extractall(path=resolved_dest)
            
            return True
            
    except Exception as e:
        # Clean up any partial extraction if it occurred
        if os.path.exists(resolved_dest):
            shutil.rmtree(resolved_dest)
        raise e
    
    return False
