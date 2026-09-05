import os
import pathlib

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    Propagate FileNotFoundError for a missing ordinary file and raise ValueError
    when the request is disallowed (path escapes root or is not an ordinary file).
    """
    root_path = pathlib.Path(reports_root).resolve()
    requested_path = pathlib.Path(filename)
    
    # Normalize the requested path to remove . and .. segments
    normalized_path = requested_path.resolve()
    
    # Check if the normalized path (without following symlinks yet) escapes the root
    if not normalized_path.is_relative_to(root_path):
        raise ValueError("Requested path escapes reports_root")
    
    # Resolve the complete target path, following symbolic links
    resolved_target = normalized_path.resolve()
    
    # Check if the fully resolved target remains inside reports_root
    if not resolved_target.is_relative_to(root_path):
        raise ValueError("Resolved target escapes reports_root")
    
    # Check if the resolved path is an ordinary file
    if not resolved_target.is_file():
        raise FileNotFoundError(f"File not found: {filename}")
    
    # Read and return the UTF-8 text
    with open(resolved_target, 'r', encoding='utf-8') as f:
        return f.read()
