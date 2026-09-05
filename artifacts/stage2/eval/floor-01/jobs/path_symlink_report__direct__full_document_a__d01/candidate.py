import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    Propagates FileNotFoundError for a missing ordinary file and raises ValueError when the request is disallowed.
    """
    # Construct the absolute path
    target_path = os.path.abspath(os.path.join(reports_root, filename))
    
    # Check if the file exists
    if not os.path.isfile(target_path):
        raise FileNotFoundError(f"File not found: {target_path}")
    
    # Safety Policy Clause 1: Reject symbolic links beneath the root
    if os.path.islink(target_path):
        raise ValueError("Access to symbolic link is disallowed")
    
    # Additional safety check: Ensure the resolved path is still within the root
    # This handles cases where a symlink might resolve outside the root (though islink check above covers the link itself)
    # We also verify the directory part is within root to prevent directory traversal via the filename component
    root_dir = os.path.abspath(reports_root)
    if not target_path.startswith(root_dir + os.sep) and target_path != root_dir:
        raise ValueError("Path traversal attempt detected")
    
    # Read the file content
    with open(target_path, 'r', encoding='utf-8') as f:
        return f.read()
