import os

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Args:
        filename: The name of the report file to read.
        reports_root: The root directory where reports are stored.
    
    Returns:
        The content of the report as a UTF-8 string.
    
    Raises:
        FileNotFoundError: If the requested file does not exist.
        ValueError: If the requested path escapes reports_root or contains symbolic links.
    """
    resolved_root = os.path.abspath(reports_root)
    resolved_filename = os.path.abspath(filename)
    
    # Normalize the path to ensure no .. segments and resolve any . segments
    normalized_filename = os.path.normpath(resolved_filename)
    
    # Check if the normalized path is within the reports_root
    if not normalized_filename.startswith(resolved_root + os.sep) and normalized_filename != resolved_root:
        raise ValueError("Path escapes reports_root")
    
    # Check for symbolic links in the path components
    path_parts = normalized_filename.split(os.sep)
    for i, part in enumerate(path_parts):
        if part == '..':
            raise ValueError("Path contains .. segment")
        
        current_path = os.path.join(resolved_root, *path_parts[:i+1])
        if os.path.islink(current_path):
            raise ValueError("Symbolic link found in path")
    
    # Check if the file exists and is a regular file
    if not os.path.isfile(normalized_filename):
        raise FileNotFoundError(f"File not found: {normalized_filename}")
    
    # Read the file content
    with open(normalized_filename, 'r', encoding='utf-8') as f:
        return f.read()
