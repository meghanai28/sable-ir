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
        ValueError: If the requested path escapes the reports_root or if it's not a regular file.
    """
    import os
    
    # Resolve the reports_root to an absolute path
    root = os.path.abspath(reports_root)
    
    # Join the filename with the root to get the requested path
    requested_path = os.path.join(root, filename)
    
    # Normalize the path to remove any redundant separators or current directory references
    # This helps in preventing path traversal issues early on
    requested_path = os.path.normpath(requested_path)
    
    # Resolve the full path, following symbolic links
    resolved_path = os.path.realpath(requested_path)
    
    # Check if the resolved path is within the reports_root
    # Use os.path.commonpath to ensure the path is a subdirectory or file within root
    try:
        common = os.path.commonpath([root, resolved_path])
        if common != root:
            raise ValueError("Path escapes reports_root")
    except ValueError:
        # This can happen if paths are on different drives (Windows) or invalid
        raise ValueError("Path escapes reports_root")
    
    # Check if the resolved path is a regular file
    if not os.path.isfile(resolved_path):
        raise ValueError("Requested path is not a regular file")
    
    # Check if the file exists (os.path.isfile returns False for missing files)
    if not os.path.exists(resolved_path):
        raise FileNotFoundError(f"The file '{filename}' does not exist")
    
    # Read the file content
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
