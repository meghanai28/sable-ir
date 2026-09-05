import os
import tarfile
import stat

def _normalize_path(path: str) -> str:
    """Normalize a path to remove redundant separators and resolve . and .. components."""
    return os.path.normpath(path)

def _is_within_dest(dest_path: str, member_path: str) -> bool:
    """Check if member_path is within dest_path."""
    dest_normalized = _normalize_path(dest_path)
    member_normalized = _normalize_path(member_path)
    try:
        return member_normalized.startswith(dest_normalized + os.sep) or member_normalized == dest_normalized
    except ValueError:
        return False

def _validate_member(member: tarfile.TarFileMember, dest_path: str) -> bool:
    """Validate a tar member to ensure it does not escape dest_path or have unsafe links."""
    if member.isdir():
        return True
    
    if member.type == tarfile.SYMLINK or member.type == tarfile.SYMLINKNF:
        # For symbolic links, check the link target
        if member.linkname:
            # Normalize the link target to prevent traversal
            link_target = _normalize_path(member.linkname)
            # Ensure the link target is within dest_path
            if not _is_within_dest(dest_path, link_target):
                return False
        return True
    
    if member.type == tarfile.HARDLINK:
        # For hard links, check if the link target is within dest_path
        if member.linkname:
            link_target = _normalize_path(member.linkname)
            if not _is_within_dest(dest_path, link_target):
                return False
        return True
    
    return True

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination path.
    
    Args:
        tar_path: Path to the tar archive.
        dest_path: Destination directory for extraction.
    
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    try:
        # Normalize the destination path immediately
        dest_path = _normalize_path(dest_path)
        
        # Create the destination directory if it doesn't exist
        os.makedirs(dest_path, exist_ok=True)
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Validate all members before extracting any
            for member in tar.getmembers():
                # Skip . and .. members
                if member.name == '.' or member.name == '..':
                    continue
                
                # Normalize the member's path
                member_path = _normalize_path(member.name)
                
                # Check for directory traversal
                if not _is_within_dest(dest_path, member_path):
                    return False
                
                # Validate links (symlinks and hardlinks)
                if not _validate_member(member, dest_path):
                    return False
            
            # Extract all members
            for member in tar:
                # Skip . and .. members
                if member.name == '.' or member.name == '..':
                    continue
                
                # Extract the member
                member_path = _normalize_path(member.name)
                tar.extract(member, dest_path)
            
            return True
            
    except Exception:
        return False
