import os

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Args:
        filename: The requested filename (untrusted).
        reports_root: The root directory for reports.
    
    Returns:
        The UTF-8 text of the validated report.
    
    Raises:
        FileNotFoundError: If the requested file is missing.
        ValueError: If the path escapes reports_root or follows a symlink outside reports_root.
    """
    # Normalize the reports_root to an absolute path
    reports_root = os.path.normpath(os.path.abspath(reports_root))
    
    # Construct the target path by joining reports_root and filename
    target_path = os.path.normpath(os.path.join(reports_root, filename))
    
    # Resolve the target path to check for symbolic links and absolute paths
    resolved_path = os.path.realpath(target_path)
    
    # Ensure the resolved path is within reports_root
    # We need to check if the resolved path starts with the reports_root path
    # Add a separator to avoid false matches like /usr/lib/python vs /usr/lib/python3
    if not (resolved_path.startswith(reports_root + os.sep) or resolved_path == reports_root):
        raise ValueError("Path escapes reports_root")
    
    # Check if the file exists and is a regular file
    if not os.path.isfile(resolved_path):
        raise FileNotFoundError(f"File not found: {resolved_path}")
    
    # Read the file content
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
