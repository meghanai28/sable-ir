import os

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Args:
        filename: The name of the report file.
        reports_root: The root directory where reports are stored.
        
    Returns:
        The UTF-8 text content of the report.
        
    Raises:
        FileNotFoundError: If the file does not exist or is not a regular file.
        ValueError: If the requested path escapes the reports_root directory.
    """
    # Construct the full path by joining the root and filename
    full_path = os.path.join(reports_root, filename)
    
    # Normalize the path to remove redundant separators and resolve . and ..
    # We use os.path.normpath which handles . and .. but does not follow symlinks
    normalized_path = os.path.normpath(full_path)
    
    # Resolve the path to get the absolute path, following symbolic links
    resolved_path = os.path.realpath(normalized_path)
    
    # Resolve the root directory to ensure consistent comparison
    resolved_root = os.path.realpath(reports_root)
    
    # Check if the resolved path is within the resolved root directory
    # This prevents directory traversal attacks even if symlinks are involved
    try:
        # Use os.path.commonpath to ensure the path is strictly within the root
        common = os.path.commonpath([resolved_root, resolved_path])
        if common != resolved_root:
            raise ValueError("Path escapes reports_root")
    except ValueError:
        # This can happen if the paths are on different drives (Windows) or invalid
        raise ValueError("Path escapes reports_root")
    
    # Check if the file exists and is a regular file
    if not os.path.isfile(resolved_path):
        raise FileNotFoundError(f"File not found: {resolved_path}")
    
    # Read and return the UTF-8 content
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
