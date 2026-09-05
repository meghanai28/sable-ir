def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    Propagate FileNotFoundError for a missing ordinary file and raise ValueError
    when the request is disallowed (path escapes root or is a symlink outside root).
    """
    import os
    import urllib.parse
    
    # Ensure reports_root is absolute
    if not os.path.isabs(reports_root):
        reports_root = os.path.abspath(reports_root)
    
    # Normalize the filename to remove . and .. segments
    # We use os.path.normpath to handle .. and . segments
    normalized_filename = os.path.normpath(filename)
    
    # Construct the requested path
    requested_path = os.path.normpath(os.path.join(reports_root, normalized_filename))
    
    # Resolve the target path, following symbolic links
    # We need to resolve the symlink to check if the final target is within the root
    try:
        resolved_target = os.path.realpath(requested_path)
    except (OSError, ValueError):
        raise ValueError("Path resolution failed")
    
    # Check if the resolved target is within reports_root
    # We must ensure the resolved path starts with the root directory
    root_prefix = reports_root + os.sep if not reports_root.endswith(os.sep) else reports_root
    
    if not resolved_target.startswith(root_prefix):
        raise ValueError("Path escapes reports_root")
    
    # Verify it's an ordinary file
    if not os.path.isfile(requested_path):
        raise FileNotFoundError(f"File not found: {filename}")
    
    # Read the file content as UTF-8
    with open(requested_path, 'r', encoding='utf-8') as f:
        return f.read()
