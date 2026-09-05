import os

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    Propagate FileNotFoundError for a missing ordinary file and raise ValueError
    when the request is disallowed (e.g., path traversal, symlinks, or escape).
    """
    # Resolve the base directory to a canonical absolute path
    resolved_root = os.path.realpath(reports_root)
    
    # Normalize the requested filename to an absolute path
    requested_path = os.path.abspath(filename)
    
    # Ensure the resolved path starts with the reports_root directory
    # This check handles cases where .. segments might be used
    if not requested_path.startswith(resolved_root + os.sep) and requested_path != resolved_root:
        raise ValueError("Path traversal detected: request escapes reports_root")
    
    # Resolve the full path to canonical form to detect symlinks
    resolved_path = os.path.realpath(requested_path)
    
    # Check if the resolved path escapes the reports_root
    if not resolved_path.startswith(resolved_root + os.sep) and resolved_path != resolved_root:
        raise ValueError("Path traversal detected: request escapes reports_root")
    
    # Walk each user-selected path component and check for symbolic links
    # We need to check all components from the root down to the filename
    parts = resolved_path.split(os.sep)
    current_path = resolved_root
    
    for part in parts:
        if part == '' or part == '.':
            continue
        next_path = os.path.join(current_path, part)
        
        # Check if the next_path is a symbolic link
        if os.path.islink(next_path):
            raise ValueError("Symbolic link detected in path")
        
        current_path = next_path
    
    # Verify the final resolved path is within reports_root
    if not resolved_path.startswith(resolved_root + os.sep) and resolved_path != resolved_root:
        raise ValueError("Path traversal detected: request escapes reports_root")
    
    # Check if the file exists and is a regular file
    if not os.path.isfile(resolved_path):
        raise FileNotFoundError(f"File not found: {resolved_path}")
    
    # Read the file content as UTF-8
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
