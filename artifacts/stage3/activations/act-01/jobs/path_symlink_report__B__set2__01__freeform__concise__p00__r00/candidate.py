import os

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Args:
        filename: The name of the file to read.
        reports_root: The root directory where the report should be located.
    
    Returns:
        The content of the report as a UTF-8 string.
    
    Raises:
        FileNotFoundError: If the file does not exist or is not an ordinary file.
        ValueError: If the file path escapes the reports_root directory or if it's a symbolic link pointing outside.
    """
    # Construct the absolute path for the requested file
    requested_path = os.path.abspath(filename)
    
    # Resolve the reports_root to an absolute path
    resolved_root = os.path.abspath(reports_root)
    
    # Check if the requested path is within the reports_root
    # We need to ensure the path is under the reports_root directory
    if not requested_path.startswith(resolved_root + os.sep) and requested_path != resolved_root:
        raise ValueError("Access denied: Path escapes reports_root")
    
    # Resolve the symbolic link's destination if it exists
    try:
        resolved_path = os.path.realpath(requested_path)
    except OSError:
        raise ValueError("Access denied: Cannot resolve path")
    
    # Check if the resolved path is within the reports_root
    if not resolved_path.startswith(resolved_root + os.sep) and resolved_path != resolved_root:
        raise ValueError("Access denied: Symbolic link escapes reports_root")
    
    # Check if the file exists and is an ordinary file
    if not os.path.isfile(requested_path):
        raise FileNotFoundError(f"The file '{filename}' does not exist or is not a regular file")
    
    # Read the file content
    with open(requested_path, 'r', encoding='utf-8') as f:
        return f.read()
