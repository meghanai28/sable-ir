import os
import stat
import pathlib


def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Args:
        filename: The name of the report file to read.
        reports_root: The root directory where the report should be located.
    
    Returns:
        The UTF-8 text of the report.
    
    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the path escapes reports_root or contains unsafe components.
    """
    # Convert inputs to pathlib objects for consistent handling
    root = pathlib.Path(reports_root).resolve()
    target = pathlib.Path(filename)
    
    # Resolve the target path relative to the root if it's not absolute
    if target.is_absolute():
        # If the filename is absolute, we must ensure it's within the root
        resolved_target = target.resolve()
    else:
        resolved_target = (root / target).resolve()
    
    # Normalize the path to remove .. and . components
    normalized_path = resolved_target.resolve()
    
    # Ensure the resolved path is within the reports_root
    try:
        normalized_path.relative_to(root)
    except ValueError:
        raise ValueError("The requested path escapes the reports_root directory.")
    
    # Check for symbolic links at any level of the path components
    # We need to check each component to ensure no symlink escapes or is dangerous
    parts = normalized_path.parts
    current_path = root
    
    for part in parts:
        # Check if the current path is a symlink
        if current_path.is_symlink():
            raise ValueError("Symbolic link detected in the path components.")
        
        # Check if the next part exists and is a symlink
        next_path = current_path / part
        if next_path.exists() and next_path.is_symlink():
            raise ValueError("Symbolic link detected in the path components.")
        
        # If the part doesn't exist yet, we still need to check if the directory exists
        # But we only care about symlinks in the path components
        current_path = next_path
    
    # Final check to ensure the file exists and is a regular file
    if not normalized_path.exists():
        raise FileNotFoundError(f"The file '{filename}' does not exist.")
    
    if not normalized_path.is_file():
        raise ValueError(f"The path '{filename}' is not a regular file.")
    
    # Read the file content
    with open(normalized_path, 'r', encoding='utf-8') as f:
        return f.read()
