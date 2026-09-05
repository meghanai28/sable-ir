import os
import sys

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Args:
        filename: The name of the report file to read.
        reports_root: The root directory where reports are stored.
        
    Returns:
        The UTF-8 text content of the report.
        
    Raises:
        ValueError: If the resolved path escapes reports_root or is not an ordinary file.
        FileNotFoundError: If the file does not exist.
    """
    # Construct the full path by joining reports_root and filename
    # This handles cases where filename might be absolute or relative
    full_path = os.path.join(reports_root, filename)
    
    # Normalize the path to remove redundant separators and resolve . and ..
    # This does NOT follow symlinks yet, but ensures the path is clean
    normalized_path = os.path.normpath(full_path)
    
    # Resolve the path, following symbolic links to get the real path
    # This is crucial for the guard: we must ensure the actual file location is within reports_root
    try:
        resolved_path = os.path.realpath(normalized_path)
    except (OSError, ValueError):
        raise ValueError(f"Invalid path: {normalized_path}")
    
    # Get the absolute path of the reports_root to compare against
    root_abs = os.path.abspath(reports_root)
    
    # Guard: Check if the resolved path is within the reports_root directory
    # We use os.path.commonpath to ensure the resolved path is a subdirectory or file within root_abs
    try:
        common = os.path.commonpath([root_abs, resolved_path])
        if common != root_abs:
            raise ValueError(f"Access denied: path {filename} escapes reports_root")
    except ValueError:
        # This can happen if paths are on different drives (Windows) or incompatible separators
        raise ValueError(f"Invalid path structure: {filename}")
    
    # Check if the resolved path is a regular file
    if not os.path.isfile(resolved_path):
        # If it's not a file (could be a directory, symlink to dir, or missing),
        # the behavior depends on the spec. The spec says "Propagate FileNotFoundError for a missing ordinary file".
        # If it's not a file (e.g., directory), it's not an ordinary file, so we should raise ValueError to disallow.
        # However, if the file is missing, os.path.isfile returns False.
        # The spec says "raise ValueError when the request is disallowed".
        # A missing file is technically disallowed to read as a report.
        # But the spec also says "Propagate FileNotFoundError for a missing ordinary file".
        # This implies if it exists but is not a file (e.g. dir), it's disallowed (ValueError).
        # If it doesn't exist, it's FileNotFoundError.
        # Wait, if os.path.isfile is False because it's missing, that's FileNotFoundError.
        # If os.path.isfile is False because it's a symlink to a dir or a dir, that's ValueError.
        # So we check if it's a file. If not, it's either missing or not a file.
        # If it's missing, we raise FileNotFoundError.
        # If it's not a file (e.g. dir), we raise ValueError.
        # But how do we distinguish?
        # os.path.isfile returns False for both.
        # We can check os.path.exists.
        if not os.path.exists(resolved_path):
            raise FileNotFoundError(f"File not found: {filename}")
        else:
            # It exists but is not a file (e.g. directory, or broken symlink to non-file)
            raise ValueError(f"Request disallowed: {filename} is not an ordinary file")
    
    # Now we know it's a valid ordinary file within the allowed directory.
    # Read the file with UTF-8 encoding.
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
