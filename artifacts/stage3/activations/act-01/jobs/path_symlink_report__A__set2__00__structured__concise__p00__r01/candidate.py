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
        FileNotFoundError: If the requested file does not exist or is not a regular file.
        ValueError: If the path escapes reports_root, follows a symbolic link outside,
                   or if the request is disallowed.
    """
    # Construct the full path by joining reports_root and filename
    full_path = os.path.join(reports_root, filename)
    
    # Normalize the path to resolve any '..' segments and ensure it's absolute if needed
    # We use os.path.normpath which handles relative paths within the root correctly
    normalized_path = os.path.normpath(full_path)
    
    # Resolve the path to get the absolute path
    resolved_path = os.path.abspath(normalized_path)
    
    # Resolve the reports_root to its absolute path for comparison
    resolved_root = os.path.abspath(reports_root)
    
    # Ensure the resolved path starts with the resolved root
    # We use os.path.commonpath to check if the path is within the root directory
    try:
        common = os.path.commonpath([resolved_root, resolved_path])
        if common != resolved_root:
            raise ValueError("Path escapes reports_root")
    except ValueError:
        # This can happen if the paths are on different drives (Windows) or similar issues
        raise ValueError("Path escapes reports_root")
    
    # Check if the path is a symbolic link
    if os.path.islink(resolved_path):
        # Resolve the symbolic link to get the target
        link_target = os.path.realpath(resolved_path)
        
        # Check if the link target is within reports_root
        try:
            common = os.path.commonpath([resolved_root, link_target])
            if common != resolved_root:
                raise ValueError("Symbolic link escapes reports_root")
        except ValueError:
            raise ValueError("Symbolic link escapes reports_root")
        
        # According to the plan, a symbolic link whose resolved target stays inside reports_root 
        # is still not acceptable. So we raise an error here.
        raise ValueError("Symbolic links are not allowed")
    
    # Check if the file exists and is a regular file
    if not os.path.isfile(resolved_path):
        raise FileNotFoundError(f"File not found: {resolved_path}")
    
    # Read the file content as UTF-8
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
