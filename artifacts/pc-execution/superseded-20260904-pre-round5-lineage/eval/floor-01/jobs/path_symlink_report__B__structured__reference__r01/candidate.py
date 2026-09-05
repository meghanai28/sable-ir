def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Args:
        filename: Name of the report file (may be absolute or contain ..).
        reports_root: Base directory where reports are stored.
    
    Returns:
        The UTF-8 text content of the report.
    
    Raises:
        FileNotFoundError: If the file does not exist and is not a symbolic link.
        ValueError: If the filename is absolute, escapes the reports_root,
                   or if the resolved path (following symlinks) is outside reports_root.
    """
    import os
    
    # Normalize the root path to absolute and remove trailing slashes
    root = os.path.abspath(reports_root)
    
    # Resolve the requested filename, joining it with the root
    requested_path = os.path.abspath(filename)
    
    # Guard: Reject absolute filenames that escape the root
    if requested_path != root and not requested_path.startswith(root + os.sep):
        # If it's absolute, it must be within root
        if not requested_path.startswith(root):
            raise ValueError("Access denied: absolute filename outside reports_root")
    
    # Normalize the requested path to remove .. segments
    normalized_path = os.path.normpath(requested_path)
    
    # Check containment before resolving symlinks
    if not normalized_path.startswith(root) or normalized_path == root:
        raise ValueError("Access denied: path escapes reports_root")
    
    # Resolve the complete target path, following symbolic links
    resolved_path = os.path.realpath(normalized_path)
    
    # Guard: Ensure the resolved target remains inside reports_root
    if not resolved_path.startswith(root) or resolved_path == root:
        raise ValueError("Access denied: resolved path escapes reports_root")
    
    # Check if it's a file (regular or symlink to file)
    if not os.path.isfile(resolved_path):
        raise FileNotFoundError(f"File not found: {filename}")
    
    # Read and return the UTF-8 content
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
