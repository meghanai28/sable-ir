import os
import sys

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Args:
        filename: The name of the report file to read.
        reports_root: The root directory where reports are stored.
    
    Returns:
        The UTF-8 text content of the report file.
    
    Raises:
        FileNotFoundError: If the requested file does not exist.
        ValueError: If the requested path escapes reports_root or is disallowed.
    """
    # Ensure reports_root is absolute
    if not os.path.isabs(reports_root):
        reports_root = os.path.abspath(reports_root)
    
    # Join filename with reports_root to get the target path
    target_path = os.path.join(reports_root, filename)
    
    # Normalize the path to resolve any .. segments
    # We need to check the path before resolving symlinks for containment
    normalized_path = os.path.normpath(target_path)
    
    # Check if the normalized path (without following symlinks yet) escapes the root
    # We use os.path.realpath which resolves symlinks, so we must check containment before that
    # First, check if the path is within reports_root
    if not normalized_path.startswith(reports_root + os.sep) and normalized_path != reports_root:
        # Special case: if normalized_path is exactly reports_root, it's not a file but we should handle it
        # Actually, the requirement says "beneath reports_root", so it should start with reports_root + separator
        if normalized_path == reports_root:
            raise ValueError("Path must be beneath reports_root")
        else:
            raise ValueError("Path escapes reports_root")
    
    # Resolve the complete target path, following symbolic links
    resolved_path = os.path.realpath(normalized_path)
    
    # Check if the resolved path is still within reports_root
    if not resolved_path.startswith(reports_root + os.sep) and resolved_path != reports_root:
        raise ValueError("Resolved path escapes reports_root")
    
    # Check if the file exists and is an ordinary file
    if not os.path.isfile(resolved_path):
        raise FileNotFoundError(f"The file {filename} does not exist")
    
    # Read the file with UTF-8 encoding
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
