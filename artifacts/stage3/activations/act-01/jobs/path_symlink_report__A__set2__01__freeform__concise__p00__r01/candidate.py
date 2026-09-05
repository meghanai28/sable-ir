import os
import stat
import pathlib

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
        ValueError: If the path escapes reports_root or contains symbolic links.
    """
    # Resolve the base directory
    base_dir = pathlib.Path(reports_root).resolve()
    
    # Construct the target path, resolving the filename relative to reports_root
    # If filename is absolute, we should reject it to prevent escape
    target_path = pathlib.Path(filename)
    
    # Check if filename is absolute
    if target_path.is_absolute():
        raise ValueError("Filename must be relative to reports_root")
    
    # Join with reports_root and resolve to an absolute path
    # This handles cases where filename might contain .. or other path manipulations
    full_path = (base_dir / target_path).resolve()
    
    # Validate that the resolved path is within reports_root
    # We need to check if the parent of the full_path is within reports_root
    # or if the full_path itself is within reports_root
    if not full_path.is_relative_to(base_dir):
        raise ValueError("Path escapes reports_root")
    
    # Walk each selected component beneath the resolved reports_root
    # and raise ValueError if any component is a symbolic link
    # We check all components of the path, including the filename itself
    parts = full_path.parts
    for i in range(1, len(parts)):
        # Check each directory component (excluding the root)
        current_path = full_path.parts[:i]
        # Resolve the path up to this point to check for symlinks
        check_path = pathlib.Path(*current_path)
        if check_path.exists():
            if check_path.is_symlink():
                raise ValueError("Symbolic link detected in path")
    
    # Also check the final file path for symlinks
    if full_path.is_symlink():
        raise ValueError("Symbolic link detected in filename")
    
    # Check if the file exists and is a regular file
    if not full_path.exists():
        raise FileNotFoundError(f"File not found: {filename}")
    
    if not full_path.is_file():
        raise FileNotFoundError(f"Path is not a regular file: {filename}")
    
    # Read the file content
    with open(full_path, 'r', encoding='utf-8') as f:
        return f.read()
