import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Args:
        filename: The requested file name (untrusted input).
        reports_root: The root directory where reports are stored.
    
    Returns:
        The UTF-8 text content of the validated report.
    
    Raises:
        FileNotFoundError: If the requested file does not exist or is not a regular file.
        ValueError: If the resolved path escapes reports_root or follows a symlink outside of it.
    """
    # Resolve the reports_root to an absolute path to ensure consistent handling
    resolved_root = os.path.abspath(reports_root)
    
    # Resolve the requested filename to an absolute path
    requested_path = os.path.abspath(filename)
    
    # Normalize the path to remove redundant separators and resolve . and ..
    # We need to be careful here; we want to check the canonical path of the target
    # but we must ensure we don't follow symlinks until the final check.
    
    # First, construct the full path and normalize it
    full_path = os.path.normpath(os.path.join(resolved_root, filename))
    
    # Check if the path starts with the reports_root directory
    # We use os.path.commonpath or simple prefix check, but for security,
    # we must ensure the resolved path is within the reports_root directory.
    # A robust way is to check if the normalized path starts with the root + separator.
    if not (full_path == resolved_root or full_path.startswith(resolved_root + os.sep)):
        raise ValueError("Path escapes reports_root")
    
    # Resolve the path following symbolic links to get the canonical path
    # This is necessary to detect if a symlink points outside the allowed directory
    try:
        resolved_path = os.path.realpath(full_path)
    except (OSError, ValueError):
        raise ValueError("Path resolution failed")
    
    # Ensure the resolved path is still within reports_root
    # Similar check as above but on the resolved path
    if not (resolved_path == resolved_root or resolved_path.startswith(resolved_root + os.sep)):
        raise ValueError("Resolved path escapes reports_root")
    
    # Check if the resolved path exists and is a regular file
    if not os.path.isfile(resolved_path):
        raise FileNotFoundError(f"The file {filename} does not exist or is not a regular file")
    
    # Read the file content as UTF-8
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
