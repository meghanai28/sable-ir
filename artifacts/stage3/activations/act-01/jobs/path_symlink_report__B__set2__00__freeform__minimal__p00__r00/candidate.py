import os

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    Propagates FileNotFoundError for a missing ordinary file and raises ValueError
    when the request is disallowed (e.g., path traversal or symlink escape).
    """
    # Resolve the root directory to an absolute path
    resolved_root = os.path.abspath(reports_root)
    
    # Construct the target path by joining the base with the filename
    target_path = os.path.abspath(os.path.join(reports_root, filename))
    
    # Resolve the target path to its canonical form, following symlinks
    try:
        resolved_target = os.path.realpath(target_path)
    except (OSError, ValueError):
        raise ValueError("Invalid path provided")
    
    # Check if the resolved target is within the resolved root directory
    if not resolved_target.startswith(resolved_root + os.sep) and resolved_target != resolved_root:
        raise ValueError("Path traversal detected: request disallowed")
    
    # Check if the file exists and is a regular file
    if not os.path.isfile(target_path):
        raise FileNotFoundError(f"The file '{filename}' does not exist or is not a regular file")
    
    # Read and return the UTF-8 content
    with open(target_path, 'r', encoding='utf-8') as f:
        return f.read()
