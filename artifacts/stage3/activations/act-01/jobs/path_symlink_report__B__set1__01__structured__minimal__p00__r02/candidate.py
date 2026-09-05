import os

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Args:
        filename: The name of the report file to read.
        reports_root: The root directory where reports are stored.
        
    Returns:
        The content of the report as a UTF-8 string.
        
    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file path escapes the reports_root or is disallowed.
    """
    # Construct the requested path by joining filename with reports_root
    requested_path = os.path.join(reports_root, filename)
    
    # Resolve the canonical path, following symbolic links
    try:
        resolved_path = os.path.realpath(requested_path)
    except (OSError, ValueError):
        raise ValueError(f"Path resolution failed for: {filename}")
    
    # Resolve the canonical path of the reports_root directory
    try:
        root_realpath = os.path.realpath(reports_root)
    except (OSError, ValueError):
        raise ValueError(f"Root path resolution failed for: {reports_root}")
    
    # Check if the resolved path is within the reports_root
    # Use os.path.commonpath to ensure we stay within the root
    try:
        common = os.path.commonpath([root_realpath, resolved_path])
        if common != root_realpath:
            raise ValueError(f"Path escapes reports_root: {filename}")
    except ValueError:
        raise ValueError(f"Invalid path structure: {filename}")
    
    # Verify that the resolved path is an ordinary file
    if not os.path.isfile(resolved_path):
        raise FileNotFoundError(f"File not found: {filename}")
    
    # Read the file content
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
