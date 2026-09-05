import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Args:
        filename: The name of the file to read (untrusted input).
        reports_root: The root directory where the report should be located.
    
    Returns:
        The UTF-8 text content of the report.
    
    Raises:
        FileNotFoundError: If the file does not exist or is not a regular file.
        ValueError: If the path escapes reports_root or contains symbolic links.
    """
    # Resolve the root directory to an absolute path
    resolved_root = os.path.abspath(reports_root)
    
    # Normalize the requested filename to an absolute path
    requested_path = os.path.abspath(filename)
    
    # Check if the requested path escapes the reports_root
    # We need to ensure that the resolved path starts with the resolved root
    # Using os.path.commonpath or string prefix check with normalization
    try:
        common = os.path.commonpath([resolved_root, requested_path])
        if common != resolved_root:
            raise ValueError("Path escapes reports_root")
    except ValueError:
        # This can happen if paths are on different drives (Windows) or invalid
        raise ValueError("Path escapes reports_root")
    
    # Construct the full path to the file
    full_path = os.path.join(resolved_root, filename)
    
    # Normalize the full path to resolve any .. or . segments
    normalized_path = os.path.normpath(full_path)
    
    # Re-check normalization to ensure no escape occurred after normalization
    try:
        common = os.path.commonpath([resolved_root, normalized_path])
        if common != resolved_root:
            raise ValueError("Path escapes reports_root after normalization")
    except ValueError:
        raise ValueError("Path escapes reports_root after normalization")
    
    # Walk each selected component beneath the resolved reports_root
    # This checks for symbolic links at each component of the path
    parts = normalized_path.split(os.sep)
    current_path = resolved_root
    
    for part in parts:
        if part == '':
            continue
        current_path = os.path.join(current_path, part)
        
        # Check if the component is a symbolic link
        if os.path.islink(current_path):
            raise ValueError("Symbolic link detected in path")
        
        # Also check if it's a directory (since we are walking components)
        if not os.path.isdir(current_path):
            # It might be a file, but we need to check the parent directories
            pass
    
    # Final check on the target file
    if not os.path.isfile(normalized_path):
        raise FileNotFoundError(f"File not found: {normalized_path}")
    
    if not os.path.isfile(normalized_path):
        raise FileNotFoundError(f"File not found: {normalized_path}")
    
    # Open and read the file
    with open(normalized_path, 'r', encoding='utf-8') as f:
        return f.read()
