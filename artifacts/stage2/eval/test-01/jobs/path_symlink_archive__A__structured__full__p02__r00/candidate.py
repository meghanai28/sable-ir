import os
import tarfile
import shutil

def _normalize_path(path: str) -> str:
    """Normalize a path to remove redundant separators and resolve . and .. segments safely."""
    return os.path.normpath(path)

def _is_within(dest: str, candidate: str) -> bool:
    """Check if candidate path is within dest path."""
    try:
        return candidate.startswith(dest + os.sep) or candidate == dest
    except ValueError:
        return False

def _validate_tar_members(tar_path: str, dest_path: str) -> bool:
    """Validate tar archive members for safety. Returns True if valid, False otherwise."""
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            for member in tar.getmembers():
                # Resolve the full path of the member
                full_member_path = os.path.join(dest_path, member.name)
                
                # Skip if the member name is empty
                if not member.name:
                    continue
                
                # Check for .. in the name itself
                if '..' in member.name.split(os.sep):
                    return False
                
                # Check if the resolved path escapes the destination
                # We need to resolve the path relative to dest_path first
                try:
                    resolved_member = os.path.normpath(os.path.join(dest_path, member.name))
                except ValueError:
                    return False
                
                # Ensure the resolved path is within dest_path
                if not _is_within(dest_path, resolved_member):
                    return False
                
                # Check for symbolic links or hard links
                if member.issym() or member.islnk():
                    return False
                
                # Check for device files
                if member.isdev():
                    return False
                
                # Check for block/special files
                if member.isblk() or member.ischr() or member.isfifo():
                    return False
                
                # For directories, we don't need to check links inside them during extraction
                # But we must ensure they are within dest_path (already checked above)
                
                # For regular files and directories, proceed
                continue
    except tarfile.TarError:
        return False
    except Exception:
        return False

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """Extract a tar archive beneath dest_path. Returns True on complete success, False otherwise."""
    # Normalize the destination path
    dest_path = _normalize_path(dest_path)
    
    # Validate the tar path exists
    if not os.path.isfile(tar_path):
        return False
    
    # Validate all members before extraction
    if not _validate_tar_members(tar_path, dest_path):
        return False
    
    # Extract the archive
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            for member in tar.getmembers():
                # Skip empty names
                if not member.name:
                    continue
                
                # Resolve the full path
                full_member_path = os.path.join(dest_path, member.name)
                
                # Extract the member
                if member.isdir():
                    # Create directory
                    os.makedirs(full_member_path, exist_ok=True)
                else:
                    # Extract file
                    # Use extractfile to ensure we don't extract with links
                    tar.extractfile(member)
                    shutil.copyfileobj(tar.extractfile(member), full_member_path)
    except Exception:
        return False
    
    return True
