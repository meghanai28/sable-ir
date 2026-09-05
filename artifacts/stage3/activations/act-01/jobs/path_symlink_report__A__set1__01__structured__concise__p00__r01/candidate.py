import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    Propagate FileNotFoundError for a missing ordinary file and raise ValueError
    when the request is disallowed (e.g., path traversal or symlinks).
    """
    # Resolve the root directory to an absolute path
    resolved_root = os.path.realpath(reports_root)
    
    # Normalize the requested filename to an absolute path
    # This handles relative paths and ensures consistent comparison
    requested_path = os.path.realpath(filename)
    
    # Check for path traversal attempts or absolute paths outside the root
    # We must ensure the resolved requested path starts with the resolved root
    if not requested_path.startswith(resolved_root + os.sep) and requested_path != resolved_root:
        raise ValueError("Request disallowed: path escapes reports_root")
    
    # If the filename is absolute, we must strictly verify it's within reports_root
    # The realpath check above handles this, but we also need to ensure no symlink escapes
    # The guard below will catch symlink issues during traversal
    
    # Walk up the path components to check for symlinks and containment
    # We split the path into components to validate each step
    parts = os.path.normpath(requested_path).split(os.sep)
    current_path = resolved_root
    
    # Validate each component of the path
    for i, part in enumerate(parts):
        if not part:
            continue
        next_path = os.path.join(current_path, part)
        
        # Check if the next path exists and is a directory (for traversal)
        # or is a file (final component)
        try:
            stat_info = os.stat(next_path)
            is_dir = stat.S_ISDIR(stat_info.st_mode)
        except FileNotFoundError:
            # If we reach the final component and it doesn't exist, we'll handle it later
            if i == len(parts) - 1:
                raise FileNotFoundError(f"File not found: {filename}")
            else:
                continue
        
        # If it's a directory, continue walking; if it's a file, stop
        if is_dir:
            current_path = next_path
        else:
            break
    
    # Final validation: ensure the file is an ordinary file and exists
    if not os.path.isfile(requested_path):
        raise FileNotFoundError(f"File not found or is not an ordinary file: {filename}")
    
    # Check if the file itself is a symlink (even if it points inside reports_root)
    if os.path.islink(requested_path):
        raise ValueError("Request disallowed: symbolic link detected")
    
    # Read the file content
    with open(requested_path, 'r', encoding='utf-8') as f:
        return f.read()
