import os
import stat
import logging

logger = logging.getLogger(__name__)

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    Propagate FileNotFoundError for a missing ordinary file and raise ValueError when the request is disallowed.
    """
    # Validate reports_root is within a safe directory (simulated check based on clause 1)
    # In a real implementation, ensure reports_root is a known approved filesystem root.
    if not os.path.isdir(reports_root):
        raise ValueError(f"reports_root is not a valid directory: {reports_root}")
    
    # Construct the full path
    full_path = os.path.normpath(os.path.join(reports_root, filename))
    
    # Resolve the full path to check for symlinks and ensure it's within the root (Clause 1)
    resolved_path = os.path.realpath(full_path)
    
    # Check if the resolved path is within the approved root
    try:
        resolved_path = os.path.realpath(reports_root)
    except (OSError, ValueError):
        raise ValueError(f"Invalid reports_root path: {reports_root}")
    
    if not resolved_path.startswith(os.path.realpath(reports_root) + os.sep) and not resolved_path == os.path.realpath(reports_root):
        raise ValueError("Resolved path is outside the approved filesystem root.")
    
    # Check if the file exists
    if not os.path.isfile(full_path):
        raise FileNotFoundError(f"File not found: {full_path}")
    
    # Check if the file is a symbolic link (Clause 1)
    if os.path.islink(full_path):
        raise ValueError("Symbolic links are not allowed.")
    
    # Check if the file is a device file or other special entries (Clause 6)
    try:
        file_stat = os.stat(full_path)
        if file_stat.st_mode & stat.S_IFMT != stat.S_IFREG:
            raise ValueError(f"Special file type not allowed: {full_path}")
    except OSError as e:
        raise ValueError(f"Error accessing file: {full_path}") from e
    
    # Read the file content
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        raise ValueError(f"Error reading file: {full_path}") from e
