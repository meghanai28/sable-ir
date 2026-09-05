import os
import tarfile
import stat
import shutil
import tempfile

def _normalize_path(path: str) -> str:
    """Normalize path by removing redundant separators and resolving . and .."""
    # Remove trailing slashes
    if path.endswith(os.sep):
        path = path[:-1]
    # Resolve . and .. components
    parts = path.split(os.sep)
    normalized_parts = []
    for part in parts:
        if part == '' or part == '.':
            continue
        elif part == '..':
            if normalized_parts:
                normalized_parts.pop()
            # If we hit .. at root, it's an escape attempt
            elif not normalized_parts:
                raise ValueError(f"Path {path} escapes root directory")
        else:
            normalized_parts.append(part)
    return os.sep.join(normalized_parts)

def _is_under_dest(member_path: str, dest_path: str) -> bool:
    """Check if member_path is under dest_path."""
    try:
        member_path = os.path.normpath(member_path)
        dest_path = os.path.normpath(dest_path)
        return member_path.startswith(dest_path + os.sep) or (dest_path and member_path == dest_path)
    except:
        return False

def _validate_and_extract_member(member: tarfile.TarFileMember, dest_path: str, tar_path: str) -> bool:
    """
    Validate a single archive member and extract it if valid.
    Returns True if successful, False otherwise.
    """
    try:
        # Determine the full destination path for this member
        if member.isdir():
            dest_member_path = os.path.join(dest_path, member.name)
            os.makedirs(dest_member_path, exist_ok=True)
        else:
            # Ensure parent directory exists
            parent_dir = os.path.dirname(dest_member_path)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)
            dest_member_path = os.path.join(dest_path, member.name)

        # Check if the member name itself escapes dest_path
        if not _is_under_dest(member.name, dest_path):
            return False

        # Handle symbolic links
        if member.issym() or member.islnk():
            # Resolve the link target
            link_target = member.linkname
            # Normalize the link target to check for escapes
            try:
                resolved_link = os.path.normpath(os.path.join(dest_member_path, link_target))
                # Check if resolved link escapes dest_path
                if not _is_under_dest(resolved_link, dest_path):
                    return False
            except:
                return False

        # Extract the member
        if member.isdir():
            # Already handled above, but ensure no data extraction happens
            pass
        else:
            # Extract file content
            with tarfile.open(tar_path, 'r:*') as tar:
                tar.extract(member, dest_path)

        return True

    except Exception as e:
        return False

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict path validation.
    Returns True on complete success, False on any failure.
    """
    try:
        # Normalize dest_path immediately
        normalized_dest = _normalize_path(dest_path)
        
        # Validate dest_path doesn't escape root
        if not normalized_dest.startswith('.') and not normalized_dest.startswith('/'):
            # If it's not absolute, treat as relative to current dir, but check for ..
            if '..' in normalized_dest.split(os.sep):
                raise ValueError(f"dest_path contains .. segments: {dest_path}")
        
        # Open the archive
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get all members
            members = tar.getmembers()
            
            for member in members:
                # Validate member name
                if not _is_under_dest(member.name, normalized_dest):
                    return False
                
                # Validate link targets if present
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    # Normalize link target to check for escapes
                    try:
                        resolved_link = os.path.normpath(os.path.join(normalized_dest, link_target))
                        if not _is_under_dest(resolved_link, normalized_dest):
                            return False
                    except:
                        return False
                
                # Extract member
                if not _validate_and_extract_member(member, normalized_dest, tar_path):
                    return False
            
            return True

    except Exception as e:
        return False
