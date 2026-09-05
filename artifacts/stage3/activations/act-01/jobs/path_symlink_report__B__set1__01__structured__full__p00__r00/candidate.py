def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Args:
        filename: Name of the file to read (may be absolute or relative).
        reports_root: Root directory where reports are stored.
    
    Returns:
        The content of the report file as a UTF-8 string.
    
    Raises:
        FileNotFoundError: If the file does not exist or is not an ordinary file.
        ValueError: If the resolved path escapes reports_root or is a directory.
    """
    import os
    
    # Resolve the base directory
    root_dir = os.path.realpath(reports_root)
    
    # Construct the full path to the requested file
    full_path = os.path.realpath(os.path.join(root_dir, filename))
    
    # Check if the resolved path is within the root directory
    if not full_path.startswith(root_dir + os.sep) and full_path != root_dir:
        raise ValueError("Access denied: path escapes reports_root")
    
    # Check if the file exists and is an ordinary file
    if not os.path.isfile(full_path):
        raise FileNotFoundError(f"File not found: {filename}")
    
    # Read the file content
    with open(full_path, 'r', encoding='utf-8') as f:
        return f.read()
