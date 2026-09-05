import os
import stat
import urllib.parse

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Args:
        filename: The name of the report file to read.
        reports_root: The root directory where reports are stored.
    
    Returns:
        The content of the report as a UTF-8 string.
    
    Raises:
        FileNotFoundError: If the file does not exist or is not a regular file.
        ValueError: If the requested path escapes reports_root or contains symbolic links.
    """
    # Ensure reports_root is an absolute path
    if not os.path.isabs(reports_root):
        reports_root = os.path.abspath(reports_root)
    
    # Resolve the target path
    target_path = os.path.abspath(filename)
    
    # Check if the path is absolute and escapes the root
    if target_path.startswith(os.path.sep) or target_path.startswith(reports_root + os.path.sep):
        raise ValueError("Path escapes reports_root")
    
    # Normalize the path to resolve .. and .
    normalized_path = os.path.normpath(target_path)
    
    # Check if the normalized path is still within the root
    if not normalized_path.startswith(reports_root + os.path.sep) and normalized_path != reports_root:
        raise ValueError("Path escapes reports_root")
    
    # Resolve the root to an absolute path
    resolved_root = os.path.realpath(reports_root)
    
    # Check if the normalized path is within the resolved root
    if not normalized_path.startswith(resolved_root + os.path.sep) and normalized_path != resolved_root:
        raise ValueError("Path escapes resolved reports_root")
    
    # Check for symbolic links in the path components
    parts = normalized_path.split(os.sep)
    current_path = ""
    
    for part in parts:
        if part == "" or part == ".":
            continue
        current_path = os.path.join(current_path, part)
        
        if os.path.islink(current_path):
            raise ValueError("Symbolic link detected in path")
    
    # Check if the final path is a symbolic link
    if os.path.islink(normalized_path):
        raise ValueError("Symbolic link detected in target path")
    
    # Check if the file exists and is a regular file
    if not os.path.isfile(normalized_path):
        raise FileNotFoundError(f"File not found: {normalized_path}")
    
    # Read the file
    with open(normalized_path, 'r', encoding='utf-8') as f:
        return f.read()
