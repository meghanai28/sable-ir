import os

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Args:
        filename: Untrusted input filename.
        reports_root: Root directory for allowed reports.
    
    Returns:
        UTF-8 text of the report.
    
    Raises:
        FileNotFoundError: If the file is missing.
        ValueError: If the path escapes reports_root or is disallowed.
    """
    # Construct the absolute path for reports_root
    root_dir = os.path.abspath(reports_root)
    
    # Join the filename with the root directory
    full_path = os.path.abspath(os.path.join(root_dir, filename))
    
    # Normalize the requested path to remove redundant separators and resolve . and ..
    normalized_path = os.path.normpath(full_path)
    
    # Check if the normalized path escapes the reports_root directory
    if not normalized_path.startswith(root_dir + os.sep) and normalized_path != root_dir:
        raise ValueError("Path escapes reports_root")
    
    # Resolve the entire path, following symbolic links
    resolved_path = os.path.realpath(normalized_path)
    
    # Check if the resolved destination remains inside reports_root
    # We need to ensure the resolved path is within the root directory
    if not resolved_path.startswith(root_dir + os.sep) and resolved_path != root_dir:
        raise ValueError("Resolved path escapes reports_root")
    
    # Check if the resolved path is a file (not a directory or symlink to directory)
    if not os.path.isfile(resolved_path):
        raise FileNotFoundError(f"File not found: {resolved_path}")
    
    # Read the file content
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
