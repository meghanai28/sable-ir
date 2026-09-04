import os
import tarfile
from typing import Optional

def _is_safe_path(member_path: str, dest_path: str) -> Optional[str]:
    """Normalize member path and return absolute path if strictly beneath dest_path, else None."""
    # Normalize the path to remove .. and . components
    normalized = os.path.normpath(member_path)
    # Reject absolute paths and paths that escape via ..
    if os.path.isabs(normalized):
        return None
    # Join with dest_path and get absolute path
    abs_path = os.path.abspath(os.path.join(dest_path, normalized))
    # Ensure the resolved path is strictly beneath dest_path
    dest_abs = os.path.abspath(dest_path)
    # Add trailing separator to dest_abs for proper prefix check
    dest_prefix = dest_abs + os.sep
    if not abs_path.startswith(dest_prefix) and abs_path != dest_abs:
        return None
    # Also reject if it's exactly dest_abs but member is not empty (would overwrite dest_path itself)
    # Empty member name "." is handled by normpath becoming "."
    if abs_path == dest_abs and normalized not in ('.', ''):
        return None
    return abs_path

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        # Ensure dest_path exists and is a directory
        if not os.path.isdir(dest_path):
            try:
                os.makedirs(dest_path, exist_ok=True)
            except OSError:
                return False
        
        with tarfile.open(tar_path, 'r:*') as tf:
            for member in tf.getmembers():
                # Reject symbolic links
                if member.issym() or member.islnk():
                    return False
                
                # Reject hard links (tarfile.islnk() covers hard links, but double-check)
                if member.islnk():
                    return False
                
                # Validate member type: only regular files and directories permitted
                if not (member.isfile() or member.isdir()):
                    return False
                
                # Validate path boundary
                safe_path = _is_safe_path(member.name, dest_path)
                if safe_path is None:
                    return False
                
                # Additional check for link targets if any (should be rejected above, but defense in depth)
                if member.linkname:
                    return False
                
                # Perform extraction for validated member
                try:
                    if member.isfile():
                        # Extract file, ensuring parent directory exists
                        parent_dir = os.path.dirname(safe_path)
                        os.makedirs(parent_dir, exist_ok=True)
                        # Use extractfile to get content and write manually for safety
                        fobj = tf.extractfile(member)
                        if fobj is None:
                            return False
                        with open(safe_path, 'wb') as out_f:
                            out_f.write(fobj.read())
                        # Restore permissions if needed (optional, but preserve basic mode)
                        if member.mode is not None:
                            os.chmod(safe_path, member.mode)
                    elif member.isdir():
                        os.makedirs(safe_path, exist_ok=True)
                        if member.mode is not None:
                            os.chmod(safe_path, member.mode)
                except (OSError, IOError):
                    return False
        
        return True
    except (tarfile.TarError, OSError, IOError):
        return False
