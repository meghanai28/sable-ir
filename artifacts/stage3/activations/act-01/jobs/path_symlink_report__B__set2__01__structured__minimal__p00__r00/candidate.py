import os

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Args:
        filename: The name of the report file to read.
        reports_root: The root directory where reports are stored.
    
    Returns:
        The UTF-8 text content of the report.
    
    Raises:
        FileNotFoundError: If the requested file does not exist.
        ValueError: If the requested path escapes the reports_root directory.
    """
    # Construct the full path by joining reports_root and filename
    full_path = os.path.join(reports_root, filename)
    
    # Resolve the path to its canonical form, following symbolic links
    try:
        resolved_path = os.path.realpath(full_path)
    except (OSError, ValueError):
        raise ValueError(f"Invalid path: {full_path}")
    
    # Resolve the canonical path of the reports_root directory
    try:
        resolved_root = os.path.realpath(reports_root)
    except (OSError, ValueError):
        raise ValueError(f"Invalid reports_root: {reports_root}")
    
    # Ensure the resolved path is within the reports_root directory
    if not resolved_path.startswith(resolved_root + os.sep) and resolved_path != resolved_root:
        raise ValueError("Path escapes reports_root")
    
    # Check if the file exists and is a regular file
    if not os.path.isfile(resolved_path):
        raise FileNotFoundError(f"File not found: {resolved_path}")
    
    # Read the file content
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
