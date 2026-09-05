import os

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Args:
        filename: Untrusted input filename to read.
        reports_root: Root directory where reports are stored.
    
    Returns:
        UTF-8 text content of the report.
    
    Raises:
        ValueError: If the resolved path escapes reports_root or contains symlinks.
        FileNotFoundError: If the file does not exist.
    """
    # Resolve the reports_root to an absolute path if it's not already
    if not os.path.isabs(reports_root):
        reports_root = os.path.abspath(reports_root)
    
    # Normalize the requested filename
    requested_path = os.path.normpath(filename)
    
    # Resolve the full path to be read
    full_path = os.path.normpath(os.path.join(reports_root, requested_path))
    
    # Check if the resolved path escapes the reports_root
    # We need to compare the absolute paths
    resolved_reports_root = os.path.abspath(reports_root)
    
    # Ensure the requested path is within reports_root
    if not full_path.startswith(resolved_reports_root + os.sep) and full_path != resolved_reports_root:
        raise ValueError("Path escapes reports_root")
    
    # Walk each component of the requested path beneath the resolved reports_root
    # and check for symbolic links
    parts = os.path.split(full_path)
    if len(parts) == 1:
        parts = (parts[0],)
    else:
        parts = parts[:-1] + (parts[-1],)
    
    current_path = resolved_reports_root
    for part in parts:
        # Check if the current component is a symbolic link
        if os.path.islink(os.path.join(current_path, part)):
            raise ValueError("Symbolic link found in path")
        
        # Resolve the next part
        current_path = os.path.normpath(os.path.join(current_path, part))
    
    # Final check for the target file
    if not os.path.isfile(full_path):
        raise FileNotFoundError(f"File not found: {full_path}")
    
    # Read the file content
    with open(full_path, 'r', encoding='utf-8') as f:
        return f.read()
