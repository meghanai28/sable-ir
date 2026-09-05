import os
import tarfile
import stat


def _normalize_path(path: str) -> str:
    """Normalize a path to its absolute form without resolving symlinks."""
    return os.path.normpath(os.path.abspath(path))


def _is_within(target: str, base: str) -> bool:
    """Check if target is within base directory."""
    try:
        normalized_target = _normalize_path(target)
        normalized_base = _normalize_path(base)
        return normalized_target.startswith(normalized_base + os.sep) or normalized_target == normalized_base
    except (ValueError, TypeError):
        return False


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive beneath dest_path.
    
    Returns True on complete success, False if validation or extraction fails.
    No archive member is written outside dest_path on failure.
    """
    try:
        # Normalize and validate destination path
        normalized_dest = _normalize_path(dest_path)
        
        # Check if dest_path escapes expected boundaries if it's not absolute
        # The plan implies we trust the caller's dest_path but guard against escapes
        # We ensure we operate on the normalized absolute path
        
        # Validate that dest_path doesn't contain .. that would escape
        # Since we normalize it, we just need to ensure we don't extract outside it
        # The guard logic will catch this during member validation
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get list of all members
            members = tar.getnames()
            
            # Validate all members before extraction
            for member in members:
                # Resolve the member's path relative to dest_path
                # We need to check if the member's name (after stripping trailing slashes)
                # would place it outside the destination directory
                
                # Calculate the full path where this member would be extracted
                # If member is a directory, it goes to dest_path/member
                # If member is a file, it goes to dest_path/member
                
                # We need to check the "target" of the member
                # For regular files and directories, the target is the member name itself
                # For symlinks, hardlinks, etc., we need to check the target
                
                # Get the member info
                member_info = tar.getmember(member)
                
                # Determine the extraction path
                if member_info.isdir():
                    extract_path = os.path.join(normalized_dest, member)
                else:
                    extract_path = os.path.join(normalized_dest, member)
                
                # For symlinks and hardlinks, we need to check the target
                if member_info.issym() or member_info.islnk():
                    # Get the link target
                    link_target = member_info.linkname
                    
                    # Normalize the link target
                    normalized_link_target = _normalize_path(link_target)
                    
                    # Check if the link target escapes the destination
                    if not _is_within(normalized_link_target, normalized_dest):
                        return False
                
                # For hardlinks, we need to check the target
                elif member_info.islnk():
                    # Get the hardlink target
                    link_target = member_info.linkname
                    
                    # Normalize the link target
                    normalized_link_target = _normalize_path(link_target)
                    
                    # Check if the link target escapes the destination
                    if not _is_within(normalized_link_target, normalized_dest):
                        return False
                
                # For regular files and directories, check the member path
                else:
                    # Normalize the member path
                    normalized_member_path = _normalize_path(member)
                    
                    # Check if the member path escapes the destination
                    if not _is_within(normalized_member_path, normalized_dest):
                        return False
            
            # If validation passes, extract the archive
            tar.extractall(path=normalized_dest)
            
            return True
            
    except Exception:
        return False
