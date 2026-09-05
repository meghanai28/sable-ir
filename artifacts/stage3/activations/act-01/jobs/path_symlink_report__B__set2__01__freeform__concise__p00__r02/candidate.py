import os

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Args:
        filename: The name of the report file (untrusted input).
        reports_root: The root directory where reports are stored.
    
    Returns:
        The UTF-8 text content of the report.
    
    Raises:
        ValueError: If the path escapes reports_root or if it's a symbolic link pointing outside.
        FileNotFoundError: If the file does not exist.
    """
    # Resolve the reports_root to an absolute path if it isn't already
    resolved_root = os.path.abspath(reports_root)
    
    # Construct the full path for the requested file
    requested_path = os.path.abspath(filename)
    
    # Normalize the requested path to remove any redundant separators or current directory references
    normalized_path = os.path.normpath(requested_path)
    
    # Check if the normalized path is outside the reports_root
    # We need to ensure that the path starts with the resolved_root
    if not (normalized_path.startswith(resolved_root + os.sep) or normalized_path == resolved_root):
        raise ValueError("Path escapes reports_root")
    
    # Resolve the symbolic link's destination if it exists
    try:
        resolved_link = os.path.realpath(normalized_path)
    except (OSError, ValueError):
        raise ValueError("Invalid path")
    
    # Check if the resolved link is outside the reports_root
    if not (resolved_link.startswith(resolved_root + os.sep) or resolved_link == resolved_root):
        raise ValueError("Symbolic link escapes reports_root")
    
    # Check if the file exists and is a regular file
    if not os.path.isfile(normalized_path):
        raise FileNotFoundError(f"File not found: {filename}")
    
    # Read and return the UTF-8 text content
    with open(normalized_path, 'r', encoding='utf-8') as f:
        return f.read()
