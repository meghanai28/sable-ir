import os

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Args:
        filename: The name of the file to read.
        reports_root: The root directory where reports are stored.
    
    Returns:
        The content of the report as a UTF-8 string.
    
    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the requested path escapes the reports_root or if the file is not an ordinary file.
    """
    # Construct the absolute path for the requested file
    requested_path = os.path.abspath(filename)
    
    # Ensure reports_root is absolute
    if not os.path.isabs(reports_root):
        reports_root = os.path.abspath(reports_root)
    
    # Normalize the requested path to remove any '..' or '.' segments
    normalized_path = os.path.normpath(requested_path)
    
    # Resolve the complete target path, following symbolic links
    resolved_path = os.path.realpath(normalized_path)
    
    # Resolve the reports_root path, following any symbolic links in the root itself
    resolved_root = os.path.realpath(reports_root)
    
    # Check if the resolved path is inside the resolved root
    # Use os.path.commonpath to ensure the path is within the root directory
    try:
        common_path = os.path.commonpath([resolved_root, resolved_path])
        if common_path != resolved_root:
            raise ValueError("Path escapes reports_root")
    except ValueError:
        raise ValueError("Path escapes reports_root")
    
    # Check if the resolved path is an ordinary file
    if not os.path.isfile(resolved_path):
        raise ValueError("Request disallowed: not an ordinary file")
    
    # Check if the original file exists (for FileNotFoundError)
    if not os.path.exists(requested_path):
        raise FileNotFoundError(f"File not found: {filename}")
    
    # Read the file content
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
