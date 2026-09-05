import os
import pathlib

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    Propagate FileNotFoundError for a missing ordinary file and raise ValueError
    when the request is disallowed (e.g., absolute paths, path traversal, or symlink escapes).
    """
    # Define the root directory as a Path object for consistent handling
    root_path = pathlib.Path(reports_root)
    
    # Check if filename is an absolute path
    if os.path.isabs(filename):
        raise ValueError("Absolute filenames are not allowed")
    
    # Construct the requested path relative to the root
    requested_path = root_path / filename
    
    # Normalize the path to remove .. and . segments
    # This helps detect path traversal attempts like "reports_root/../../../etc/passwd"
    # However, we must also resolve symlinks before checking containment
    normalized_path = requested_path.resolve()
    
    # Check if the normalized path escapes the root
    # We need to ensure the resolved path starts with the root directory
    if not str(normalized_path).startswith(str(root_path)):
        # Additional check to ensure we don't match just the directory itself if it's a file
        # But primarily, the resolved path must be within the root
        raise ValueError("Path traversal detected or path escapes reports_root")
    
    # Resolve the complete target path, following symbolic links
    resolved_target = normalized_path.resolve()
    
    # Check if the fully resolved target remains inside reports_root
    # This catches cases where a symlink points outside the root
    if not str(resolved_target).startswith(str(root_path)):
        raise ValueError("Symbolic link resolves outside reports_root")
    
    # Verify the resolved path is a file and exists
    if not resolved_path.exists() or not resolved_path.is_file():
        raise FileNotFoundError(f"The file {filename} does not exist")
    
    # Read the file as UTF-8
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
