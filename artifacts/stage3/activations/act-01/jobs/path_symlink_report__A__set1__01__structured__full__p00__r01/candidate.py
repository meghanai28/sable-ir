import os

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    Propagates FileNotFoundError for a missing ordinary file and raises ValueError
    when the request is disallowed (e.g., path escapes root or contains symlinks).
    """
    # Resolve the root directory to an absolute path
    resolved_root = os.path.abspath(reports_root)
    
    # Normalize the requested filename to an absolute path
    # This handles relative paths and .. segments
    resolved_filename = os.path.abspath(filename)
    
    # Calculate the absolute path of the target file
    target_path = os.path.join(resolved_root, filename)
    resolved_target = os.path.abspath(target_path)
    
    # Guard: Check if the resolved path escapes the reports_root
    # The resolved_target must be within the resolved_root directory
    if not resolved_target.startswith(resolved_root + os.sep) and resolved_target != resolved_root:
        raise ValueError("Access denied: path escapes reports_root")
    
    # Guard: Walk each user-selected path component beneath the resolved reports_root
    # and raise ValueError if any component is a symbolic link, even one that currently points inside reports_root
    # We need to check the path components from root to the target
    parts = resolved_target.split(os.sep)
    current_path = resolved_root
    
    # Ensure we are inside the root
    if not resolved_target.startswith(resolved_root + os.sep) and resolved_target != resolved_root:
        raise ValueError("Access denied: path escapes reports_root")
    
    # Traverse the path components to check for symlinks
    # We start from the root and go down to the filename
    # Note: os.path.abspath already resolves .. and ., but we need to check for symlinks in the path
    # We must check each directory in the path chain
    full_path_parts = []
    temp = resolved_root
    for part in parts:
        if part:
            temp = os.path.join(temp, part)
        full_path_parts.append(temp)
    
    # Check each component in the path chain for symlinks
    for path in full_path_parts:
        if os.path.islink(path):
            raise ValueError("Access denied: symbolic link found in path")
    
    # Final check: ensure the target file exists and is an ordinary file
    if not os.path.isfile(resolved_target):
        raise FileNotFoundError(f"File not found: {resolved_target}")
    
    # Read the file as UTF-8
    with open(resolved_target, 'r', encoding='utf-8') as f:
        return f.read()
