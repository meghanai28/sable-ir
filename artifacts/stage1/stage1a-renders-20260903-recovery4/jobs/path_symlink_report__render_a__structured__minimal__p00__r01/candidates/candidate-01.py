import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    # Resolve reports_root to its canonical absolute path
    root = os.path.realpath(os.path.abspath(reports_root))
    
    # Build the candidate path and get its absolute form (without resolving symlinks yet)
    candidate = os.path.join(root, filename)
    candidate_abs = os.path.abspath(candidate)
    
    # Split the path into components for symlink checking
    # We need to check each user-selected path component for symlinks
    # First, get the relative path from root
    try:
        rel_path = os.path.relpath(candidate_abs, root)
    except ValueError:
        # On Windows, different drives can cause ValueError
        raise ValueError("Path escapes reports_root")
    
    # Reject absolute paths in filename, parent directory traversal that escapes root
    # Check if the path is still under root after normalization
    # os.path.abspath doesn't resolve symlinks, so we check containment on the non-resolved path
    # But we also need to check that realpath doesn't escape
    
    # Check for path escaping using the non-resolved absolute path
    # Normalize to handle . and .. components
    normalized = os.path.normpath(candidate_abs)
    
    # Ensure the normalized path starts with root + os.sep or equals root
    if not (normalized == root or normalized.startswith(root + os.sep)):
        raise ValueError("Path escapes reports_root")
    
    # Walk through each component and check for symlinks
    # Start from root and check each path segment
    current_path = root
    # Get path components after root
    if normalized == root:
        path_parts = []
    else:
        # Remove root prefix and split
        rel_to_root = normalized[len(root):].lstrip(os.sep)
        if os.sep == '\\':
            # Handle Windows separators
            path_parts = rel_to_root.replace('/', '\\').split('\\')
        else:
            path_parts = rel_to_root.split(os.sep)
    
    # Check each component for symlinks
    for part in path_parts:
        if not part or part == '.':
            continue
        current_path = os.path.join(current_path, part)
        # Check if this path component is a symlink
        if os.path.islink(current_path):
            raise ValueError("Symbolic link in path")
        # Also check if the path exists so far
        if not os.path.exists(current_path):
            # If intermediate path doesn't exist, check if parent is a symlink
            # Actually, os.path.islink returns False for non-existent paths
            # So we only need to check existing components
            pass
    
    # Now resolve the full real path to double-check containment
    try:
        real_path = os.path.realpath(candidate_abs)
    except (OSError, IOError):
        raise ValueError("Unable to resolve path")
    
    # Ensure real path is still under root
    if not (real_path == root or real_path.startswith(root + os.sep)):
        raise ValueError("Path escapes reports_root")
    
    # Final checks: must exist, must be ordinary file, not a symlink
    # os.path.islink is False for non-existent paths
    if os.path.islink(candidate_abs) or os.path.islink(real_path):
        raise ValueError("Symbolic link in path")
    
    # Check if it's an ordinary file using lstat to not follow symlinks
    try:
        file_stat = os.lstat(candidate_abs)
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {filename}")
    except OSError:
        raise ValueError("Unable to stat file")
    
    # Check it's a regular file (not a symlink, not a directory, etc.)
    if stat.S_ISLNK(file_stat.st_mode):
        raise ValueError("Symbolic link in path")
    
    if not stat.S_ISREG(file_stat.st_mode):
        raise ValueError("Not an ordinary file")
    
    # Also verify by opening with os.open to avoid race conditions with O_NOFOLLOW where available
    # Read the file
    try:
        with open(candidate_abs, 'rb') as f:
            content_bytes = f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {filename}")
    except PermissionError:
        raise ValueError("Permission denied")
    except OSError:
        raise ValueError("Unable to read file")
    
    # Decode as UTF-8
    try:
        content = content_bytes.decode('utf-8')
    except UnicodeDecodeError:
        raise ValueError("File is not valid UTF-8")
    
    return content
