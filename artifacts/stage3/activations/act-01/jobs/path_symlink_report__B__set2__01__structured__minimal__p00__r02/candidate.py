import os

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Args:
        filename: The requested file path.
        reports_root: The root directory where reports are stored.
    
    Returns:
        The UTF-8 text of the validated report.
    
    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the request is disallowed (path escapes reports_root).
    """
    # Resolve the reports_root to an absolute path
    resolved_root = os.path.abspath(reports_root)
    
    # Join the filename with the root
    requested_path = os.path.join(resolved_root, filename)
    
    # Resolve the requested path, following symbolic links
    resolved_path = os.path.realpath(requested_path)
    
    # Check if the resolved path is within the reports_root
    # Use os.path.commonpath to ensure the resolved path is inside the root
    # We need to check if the resolved path starts with the root path followed by a separator or is exactly the root
    try:
        common = os.path.commonpath([resolved_root, resolved_path])
        if common != resolved_root:
            raise ValueError("Path escapes reports_root")
    except ValueError:
        # commonpath might raise ValueError if paths are on different drives (Windows) or invalid
        raise ValueError("Path escapes reports_root")
    
    # Check if the file exists and is a regular file
    if not os.path.isfile(resolved_path):
        raise FileNotFoundError(f"The file {filename} does not exist")
    
    # Read the file content
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
