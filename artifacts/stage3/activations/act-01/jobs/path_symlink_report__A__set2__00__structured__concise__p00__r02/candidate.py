import os
import sys

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Args:
        filename: The name of the file to read.
        reports_root: The root directory where reports are stored.
    
    Returns:
        The content of the report as a UTF-8 string.
    
    Raises:
        FileNotFoundError: If the requested file does not exist.
        ValueError: If the path escapes reports_root or if it's a symbolic link
                    that escapes or points outside reports_root.
    """
    # Normalize the root directory to an absolute path to prevent directory traversal
    reports_root = os.path.normpath(os.path.abspath(reports_root))
    
    # Resolve the requested filename to an absolute path
    requested_path = os.path.abspath(filename)
    
    # Join the resolved filename with the root directory
    resolved_path = os.path.join(reports_root, requested_path)
    
    # Normalize the resolved path to handle any .. or . components
    resolved_path = os.path.normpath(resolved_path)
    
    # Ensure the resolved path is within the reports_root
    if not resolved_path.startswith(reports_root + os.sep) and resolved_path != reports_root:
        raise ValueError("Path escapes reports_root")
    
    # Check if the path is a symbolic link
    if os.path.islink(resolved_path):
        # Get the resolved target of the symbolic link
        link_target = os.path.realpath(resolved_path)
        
        # Ensure the link's target is within reports_root
        if not link_target.startswith(reports_root + os.sep) and link_target != reports_root:
            raise ValueError("Symbolic link escapes reports_root")
        
        # Even if the link's target is within reports_root, it's not acceptable
        raise ValueError("Symbolic links are not allowed")
    
    # Check if the file exists and is a regular file
    if not os.path.isfile(resolved_path):
        raise FileNotFoundError(f"The file {filename} does not exist")
    
    # Read the file content as UTF-8
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
