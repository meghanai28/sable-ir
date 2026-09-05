import os

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Args:
        filename: The requested file name (untrusted input).
        reports_root: The root directory for reports.
    
    Returns:
        The UTF-8 text of the validated report.
    
    Raises:
        FileNotFoundError: If the file is missing.
        ValueError: If the path escapes reports_root or involves a symbolic link.
    """
    # Resolve the root directory to ensure it exists and get its absolute path
    root_dir = os.path.abspath(reports_root)
    
    # Construct the full path by joining the root and the filename
    # We must use os.path.join to prevent path traversal via .. in the input
    full_path = os.path.join(root_dir, filename)
    
    # Normalize the path to remove any redundant separators or current directory references
    # This is crucial for path validation
    normalized_path = os.path.normpath(full_path)
    
    # Get the absolute path of the normalized request
    absolute_request_path = os.path.abspath(normalized_path)
    
    # Check if the absolute request path starts with the root directory
    # This prevents path traversal attacks like ../etc/passwd
    if not absolute_request_path.startswith(root_dir + os.sep) and absolute_request_path != root_dir:
        raise ValueError("Access denied: path escapes reports_root")
    
    # Check if the file exists
    if not os.path.isfile(absolute_request_path):
        raise FileNotFoundError(f"File not found: {absolute_request_path}")
    
    # Check if it's a symbolic link
    if os.path.islink(absolute_request_path):
        raise ValueError("Symbolic links are not allowed")
    
    # Now it's safe to open and read the file
    with open(absolute_request_path, 'r', encoding='utf-8') as f:
        return f.read()
