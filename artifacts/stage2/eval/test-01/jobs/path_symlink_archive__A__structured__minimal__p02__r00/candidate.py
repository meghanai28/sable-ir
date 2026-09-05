import os
import tarfile
import stat


def _normalize_path(path: str) -> str:
    """Normalize a path to remove redundant separators and resolve . and .. components safely."""
    return os.path.normpath(path)


def _is_under_destination(target: str, dest_path: str) -> bool:
    """Check if target is under dest_path, handling both absolute and relative paths."""
    dest_normalized = _normalize_path(dest_path)
    target_normalized = _normalize_path(target)
    return target_normalized.startswith(dest_normalized + os.sep) or target_normalized == dest_path


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """Extract a tar archive to dest_path, validating all paths to prevent traversal."""
    dest_path = _normalize_path(dest_path)
    
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Validate and extract members
            for member in tar.getmembers():
                # Skip symbolic links and hard links as per ORDER
                if member.issym() or member.islnk():
                    continue
                
                # Resolve the target path
                if member.isdir():
                    target_path = member.name
                else:
                    target_path = os.path.join(dest_path, member.name)
                
                # Normalize the target path
                target_normalized = _normalize_path(target_path)
                
                # Validate that the target does not escape the destination
                if not _is_under_destination(target_normalized, dest_path):
                    return False
                
                # Create parent directories if necessary
                if not member.isdir():
                    parent_dir = os.path.dirname(target_normalized)
                    if parent_dir and not os.path.exists(parent_dir):
                        os.makedirs(parent_dir)
                
                # Extract the member
                tar.extract(member, dest_path)
            
            return True
    
    except Exception:
        return False
