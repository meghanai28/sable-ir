import os
import tarfile
import stat
import shutil

def _is_within_dest(base_path: str, target_path: str) -> bool:
    """Check if target_path is within base_path, handling symlinks and .."""
    try:
        base_resolved = os.path.realpath(base_path)
        target_resolved = os.path.realpath(target_path)
        return target_resolved.startswith(base_resolved + os.sep) or target_resolved == base_resolved
    except (ValueError, OSError):
        return False

def _validate_and_extract_member(member: tarfile.TarFileMember, dest_path: str, follow_links: bool = True) -> bool:
    """Validate a single archive member and extract it if safe."""
    member_name = member.name
    member_path = os.path.join(dest_path, member_name)
    
    # Check for absolute paths or path traversal
    if os.path.isabs(member_name):
        return False
    
    # Normalize member path to handle ..
    normalized_member_path = os.path.normpath(member_name)
    full_member_path = os.path.normpath(os.path.join(dest_path, normalized_member_path))
    
    if not _is_within_dest(dest_path, full_member_path):
        return False
    
    # Check for symlinks/hardlinks
    if member.type == tarfile.SYMTYPE:
        if follow_links:
            target_path = os.path.join(dest_path, member.linkname)
            if not _is_within_dest(dest_path, target_path):
                return False
        else:
            return False
    
    if member.type == tarfile.HARDLINK:
        target_path = os.path.join(dest_path, member.linkname)
        if not _is_within_dest(dest_path, target_path):
            return False
    
    # Attempt extraction
    try:
        if member.isfile():
            os.makedirs(os.path.dirname(member_path), exist_ok=True)
            shutil.copy2(member.file, member_path)
        elif member.isdir():
            os.makedirs(member_path, exist_ok=True)
        elif member.type == tarfile.SYMTYPE:
            if follow_links:
                os.symlink(member.linkname, member_path)
            else:
                return False
        elif member.type == tarfile.HARDLINK:
            if follow_links:
                os.link(os.path.join(dest_path, member.linkname), member_path)
            else:
                return False
    except (OSError, shutil.Error):
        return False
    
    return True

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict path validation.
    Returns True only if extraction completes successfully and safely.
    """
    try:
        # Normalize dest_path
        dest_path = os.path.normpath(dest_path)
        
        # Validate dest_path does not escape root
        if not os.path.isabs(dest_path):
            dest_path = os.path.abspath(dest_path)
        
        if not _is_within_dest(os.sep, dest_path):
            return False
        
        # Open the tar archive
        with tarfile.open(tar_path, 'r:*') as tar:
            # Validate and extract each member
            for member in tar:
                # Check for path traversal in member name
                if os.path.isabs(member.name) or '..' in member.name.split(os.sep):
                    return False
                
                if not _validate_and_extract_member(member, dest_path):
                    return False
        
        return True
    
    except Exception:
        return False
