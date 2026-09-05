import os

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    Propagates FileNotFoundError for a missing ordinary file and raises ValueError
    when the request is disallowed (path escapes reports_root or follows symlinks out).
    """
    # Resolve the base root to an absolute path
    resolved_root = os.path.realpath(reports_root)
    
    # Construct the full path
    full_path = os.path.join(reports_root, filename)
    
    # Resolve the full path to check for symlinks and absolute paths
    resolved_path = os.path.realpath(full_path)
    
    # Security check: ensure the resolved path is within the reports_root
    if not resolved_path.startswith(resolved_root + os.sep) and resolved_path != resolved_root:
        raise ValueError("Path escapes reports_root")
    
    # Check if the file exists and is a regular file
    if not os.path.isfile(full_path):
        raise FileNotFoundError(f"File not found: {filename}")
    
    # Read the file
    with open(full_path, 'r', encoding='utf-8') as f:
        return f.read()
