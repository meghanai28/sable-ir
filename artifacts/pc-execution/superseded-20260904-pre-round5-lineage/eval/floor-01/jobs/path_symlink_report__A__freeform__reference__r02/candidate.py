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
        FileNotFoundError: If the file does not exist or is not a regular file.
        ValueError: If the filename is absolute, escapes the reports_root,
                    or if any path component is a symbolic link.
    """
    # Convert to pathlib.Path for easier manipulation
    root_path = pathlib.Path(reports_root).resolve()
    requested_path = pathlib.Path(filename)
    
    # Check for absolute paths
    if requested_path.is_absolute():
        raise ValueError("Absolute filenames are not allowed")
    
    # Join the requested path with the root
    joined_path = root_path / requested_path
    
    # Normalize the path to resolve .. and . segments
    normalized_path = joined_path.resolve()
    
    # Check if the normalized path escapes the root
    if not normalized_path.startswith(root_path):
        raise ValueError("Path escapes the reports_root directory")
    
    # Walk each user-selected path component and check for symbolic links
    # We need to check the path components before resolving the final path completely
    # to catch symlinks that might point outside the root or be dangerous.
    # We'll iterate through the parts of the path.
    
    current_path = root_path
    parts = list(requested_path.parts)
    
    for part in parts:
        next_path = current_path / part
        # Check if the next_path component is a symlink
        if next_path.is_symlink():
            raise ValueError("Symbolic link detected in path")
        # Also check the directory if it exists and is a symlink
        if next_path.exists():
            if next_path.is_symlink():
                raise ValueError("Symbolic link detected in path")
        current_path = next_path
    
    # Final check on the resolved path itself
    if normalized_path.is_symlink():
        raise ValueError("Symbolic link detected in final path")
    
    # Check if the file exists and is a regular file
    if not normalized_path.exists():
        raise FileNotFoundError(f"File not found: {filename}")
    
    if not normalized_path.is_file():
        raise FileNotFoundError(f"Not a regular file: {filename}")
    
    # Read the file with UTF-8 encoding
    with open(normalized_path, 'r', encoding='utf-8') as f:
        return f.read()
