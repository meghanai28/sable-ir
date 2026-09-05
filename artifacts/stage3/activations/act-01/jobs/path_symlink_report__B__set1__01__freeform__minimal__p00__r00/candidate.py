import os

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Security measures:
    - Treats filename as untrusted input.
    - Normalizes paths to prevent directory traversal.
    - Validates that the resolved path (including following symlinks) stays within reports_root.
    - Raises ValueError if the path escapes the root or is disallowed.
    - Raises FileNotFoundError if the file is missing.
    - Returns UTF-8 text of the validated report.
    """
    # Normalize the requested path to remove any .. or . segments
    # We use os.path.normpath which handles .. and . segments
    requested_path = os.path.normpath(filename)
    
    # Resolve the absolute path of the requested file
    # This will handle cases where filename is relative or absolute
    try:
        resolved_path = os.path.abspath(requested_path)
    except (ValueError, OSError):
        raise ValueError(f"Invalid path: {filename}")
    
    # Resolve the absolute path of the reports_root
    root_path = os.path.abspath(reports_root)
    
    # Check if the resolved path starts with the root path
    # We need to ensure there's no path traversal after the root
    if not resolved_path.startswith(root_path + os.sep) and resolved_path != root_path:
        # This check handles cases where the path is inside the root but doesn't start with it
        # due to trailing slashes or other edge cases
        if not resolved_path.startswith(root_path):
            raise ValueError(f"Path escapes reports_root: {resolved_path}")
    
    # Resolve the complete target path, following symbolic links
    # os.path.realpath resolves symlinks and normalizes the path
    try:
        target_path = os.path.realpath(resolved_path)
    except (ValueError, OSError):
        raise ValueError(f"Cannot resolve path: {resolved_path}")
    
    # Final containment check: the fully resolved target must be inside reports_root
    if not target_path.startswith(root_path + os.sep) and target_path != root_path:
        raise ValueError(f"Resolved path escapes reports_root: {target_path}")
    
    # Check if the target is a file and not a directory
    if not os.path.isfile(target_path):
        raise ValueError(f"Target is not a file: {target_path}")
    
    # Check if the file exists
    if not os.path.exists(target_path):
        raise FileNotFoundError(f"File not found: {target_path}")
    
    # Read the file with UTF-8 encoding
    with open(target_path, 'r', encoding='utf-8') as f:
        return f.read()
