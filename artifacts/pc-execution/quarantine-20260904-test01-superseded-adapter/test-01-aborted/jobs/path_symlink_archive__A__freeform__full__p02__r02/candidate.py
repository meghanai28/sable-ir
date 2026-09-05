import os
import tarfile
import tempfile

def _is_within_dest(base_path: str, member_path: str) -> bool:
    """Check if member_path is within base_path when resolved."""
    try:
        base_resolved = os.path.realpath(base_path)
        member_resolved = os.path.realpath(member_path)
        return member_resolved.startswith(os.path.normpath(base_resolved) + os.sep) or member_resolved == base_resolved
    except (ValueError, OSError):
        return False

def _validate_member(member: tarfile.TarFileMember, dest_path: str) -> bool:
    """Validate a tar member to ensure it's safe to extract within dest_path."""
    # Reject symbolic links
    if member.issym:
        target = member.linkname
        # Reject if target is absolute
        if os.path.isabs(target):
            return False
        # Resolve target relative to the member's location in the archive
        # The member's location in the archive is member.name
        # We need to resolve the target relative to the directory of the member
        member_dir = os.path.dirname(member.name)
        if member_dir:
            resolved_target = os.path.normpath(os.path.join(member_dir, target))
        else:
            resolved_target = target
        
        # Check if resolved target is outside dest_path
        if not _is_within_dest(dest_path, resolved_target):
            return False
        return False
    
    # Reject hard links
    if member.islnk:
        target = member.linkname
        if not _is_within_dest(dest_path, target):
            return False
        return False
    
    # Regular files and directories are safe to proceed with extraction
    return True

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive beneath dest_path.
    Returns True on complete success, False on any validation or extraction failure.
    """
    # Create a temporary directory for extraction to ensure we don't write outside dest_path
    # We will move the extracted files to dest_path only if everything is valid
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            with tarfile.open(tar_path, 'r:*') as tar:
                # First, validate all members before extracting
                for member in tar.getmembers():
                    if not _validate_member(member, dest_path):
                        return False
                
                # Extract to the temporary directory first
                tar.extractall(path=temp_dir)
                
                # Now move all extracted files to the destination directory
                # We need to preserve the directory structure relative to the archive root
                # but ensure we don't create files outside dest_path
                
                # Get the root directory of the archive
                root_dir = os.path.dirname(tar.getnames()[0]) if tar.getnames() else '.'
                
                # Map each file in temp_dir to its corresponding location in dest_path
                # We need to handle the case where the archive root is not empty
                
                # Create the destination directory structure
                for root, dirs, files in os.walk(temp_dir):
                    # Calculate relative path from the archive root
                    rel_path = os.path.relpath(root, temp_dir)
                    
                    # Determine the corresponding path in dest_path
                    if rel_path == '.':
                        dest_sub_path = dest_path
                    else:
                        dest_sub_path = os.path.join(dest_path, rel_path)
                    
                    # Ensure the directory exists
                    os.makedirs(dest_sub_path, exist_ok=True)
                    
                    # Move files
                    for file in files:
                        src_file = os.path.join(root, file)
                        dst_file = os.path.join(dest_sub_path, file)
                        
                        # If the destination exists, we might have issues, but since we extracted to temp_dir,
                        # it shouldn't exist unless the dest_path already had files
                        # However, we need to be careful about the structure
                        
                        # Actually, a simpler approach: just copy/move files from temp_dir to dest_path
                        # preserving the structure, but ensuring we don't go outside dest_path
                        
                        # Since we validated that all paths are within dest_path, we can safely move
                        if os.path.isabs(src_file):
                            # This shouldn't happen with tarfile.extractall, but just in case
                            pass
                        
                        # Move the file
                        os.rename(src_file, dst_file)
                        
        except Exception:
            return False
    
    return True
