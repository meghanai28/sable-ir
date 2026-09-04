import os

def read_report(filename: str, reports_root: str) -> str:
    # Resolve the absolute path of reports_root
    abs_reports_root = os.path.abspath(reports_root)
    
    # Join filename with reports_root and get absolute path
    requested_path = os.path.join(abs_reports_root, filename)
    abs_requested_path = os.path.abspath(requested_path)
    
    # Fully resolve symlinks to get the complete target path
    try:
        resolved_path = os.path.realpath(abs_requested_path)
    except (OSError, ValueError):
        raise ValueError("Symlink resolution failed or path traversal detected")
    
    # Verify the resolved path is inside reports_root
    # Use os.path.commonpath for reliable prefix checking
    try:
        common = os.path.commonpath([resolved_path, abs_reports_root])
    except ValueError:
        # On Windows, different drives would raise ValueError
        raise ValueError("Path traversal detected: resolved path outside approved root")
    
    if common != abs_reports_root:
        raise ValueError("Path traversal detected: resolved path outside approved root")
    
    # Verify the resolved path is an ordinary file
    if not os.path.isfile(resolved_path):
        if not os.path.exists(resolved_path):
            raise FileNotFoundError(f"File not found: {resolved_path}")
        raise ValueError("Not an ordinary file")
    
    # Read and decode as UTF-8
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
