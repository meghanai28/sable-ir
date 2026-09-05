import os

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Args:
        filename: The name of the report file to read.
        reports_root: The root directory where reports are stored.
    
    Returns:
        The UTF-8 text content of the report.
    
    Raises:
        FileNotFoundError: If the requested file does not exist.
        ValueError: If the requested path escapes reports_root or is disallowed.
    """
    # Construct the full path by joining reports_root and filename
    requested_path = os.path.join(reports_root, filename)
    
    # Normalize the requested path to remove any redundant separators or current directory references
    # This helps in detecting path traversal attempts early
    normalized_requested_path = os.path.normpath(requested_path)
    
    # Resolve the actual target path, following symbolic links
    resolved_target_path = os.path.realpath(normalized_requested_path)
    
    # Resolve the reports_root to its canonical form to ensure consistent comparison
    resolved_reports_root = os.path.realpath(reports_root)
    
    # Check if the resolved target path is outside the reports_root directory
    # This guards against path traversal attacks even if the input filename looks safe
    if not resolved_target_path.startswith(resolved_reports_root + os.sep) and resolved_target_path != resolved_reports_root:
        raise ValueError("The requested path escapes the reports_root directory.")
    
    # Verify that the resolved path is an ordinary file (not a directory or symlink to directory)
    if not os.path.isfile(resolved_target_path):
        raise FileNotFoundError(f"The file {filename} does not exist.")
    
    # Attempt to read the file with UTF-8 encoding
    try:
        with open(resolved_target_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        raise
