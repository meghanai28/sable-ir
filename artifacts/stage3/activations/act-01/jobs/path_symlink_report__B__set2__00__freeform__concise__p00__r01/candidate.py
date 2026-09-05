import os

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    Propagate FileNotFoundError for a missing ordinary file and raise ValueError
    when the request is disallowed (path escapes reports_root).
    """
    # Resolve the reports_root to an absolute path to ensure consistent comparison
    resolved_reports_root = os.path.abspath(reports_root)
    
    # Construct the full path by joining reports_root and filename
    # This handles cases where filename is absolute or relative
    full_path = os.path.abspath(os.path.join(reports_root, filename))
    
    # Resolve the full path to its canonical location, following symbolic links
    try:
        resolved_path = os.path.realpath(full_path)
    except (OSError, ValueError):
        raise ValueError("Invalid path provided")
    
    # Ensure the resolved path is within the reports_root directory
    # We use os.path.commonpath to check if the resolved path is under reports_root
    try:
        common = os.path.commonpath([resolved_reports_root, resolved_path])
        if common != resolved_reports_root:
            raise ValueError("Path escapes reports_root")
    except ValueError:
        raise ValueError("Invalid path structure")
    
    # Check if the file exists and is a regular file
    if not os.path.isfile(full_path):
        raise FileNotFoundError(f"File not found: {filename}")
    
    # Read the file content
    with open(full_path, 'r', encoding='utf-8') as f:
        return f.read()
