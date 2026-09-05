import os

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Args:
        filename: Untrusted input filename.
        reports_root: Root directory where reports are located.
    
    Returns:
        UTF-8 text of the validated report.
    
    Raises:
        FileNotFoundError: If the requested file does not exist.
        ValueError: If the path escapes reports_root or is disallowed.
    """
    # Normalize the base root to avoid directory traversal issues
    resolved_root = os.path.normpath(os.path.abspath(reports_root))
    
    # Join the filename with the root
    requested_path = os.path.normpath(os.path.join(resolved_root, filename))
    
    # Check if the path starts with the root (handles .. and absolute paths)
    # Use os.path.commonpath to ensure the path is within the root
    try:
        common_path = os.path.commonpath([resolved_root, requested_path])
        if common_path != resolved_root:
            raise ValueError("Path escapes reports_root")
    except ValueError:
        # This can happen if paths are on different drives (Windows) or invalid
        raise ValueError("Path escapes reports_root")
    
    # Resolve the path following symbolic links
    resolved_path = os.path.realpath(requested_path)
    
    # Check if the resolved path is still within the root
    try:
        common_path_resolved = os.path.commonpath([resolved_root, resolved_path])
        if common_path_resolved != resolved_root:
            raise ValueError("Symbolic link escapes reports_root")
    except ValueError:
        raise ValueError("Symbolic link escapes reports_root")
    
    # Check if it's an ordinary file
    if not os.path.isfile(resolved_path):
        raise FileNotFoundError(f"File not found: {filename}")
    
    # Read and return the file content
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
