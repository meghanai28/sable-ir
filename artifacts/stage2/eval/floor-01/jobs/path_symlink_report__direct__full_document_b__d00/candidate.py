import os
import re

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Security considerations applied:
    1. Filesystem root validation: Ensures the resolved path is within the approved root.
    2. Symbolic link handling: Resolves complete target path and verifies it remains within root.
    3. Input validation: Rejects paths containing null bytes or other dangerous characters.
    """
    # Validate that filename and reports_root are not empty
    if not filename or not reports_root:
        raise ValueError("Filename and reports_root must be non-empty strings")
    
    # Check for null bytes in input (common injection vector)
    if '\0' in filename or '\0' in reports_root:
        raise ValueError("Null bytes not allowed in paths")
    
    # Construct the absolute path for the requested file
    requested_path = os.path.join(reports_root, filename)
    
    # Resolve the full path to catch symlink attacks
    resolved_path = os.path.realpath(requested_path)
    
    # Ensure the resolved path is within the approved root
    # Normalize both paths to handle trailing slashes and ensure prefix match
    root_normalized = os.path.normpath(reports_root)
    target_normalized = os.path.normpath(resolved_path)
    
    # Check if target is under root. Use os.path.commonpath for robust prefix checking
    try:
        common = os.path.commonpath([root_normalized, target_normalized])
        if common != root_normalized:
            raise ValueError("Access denied: Path is outside the approved root")
    except ValueError:
        # This can happen if paths are on different drives (Windows) or have different root styles
        raise ValueError("Access denied: Invalid path structure")
    
    # Verify the file exists and is a regular file (not a directory)
    if not os.path.isfile(resolved_path):
        raise FileNotFoundError(f"File not found: {filename}")
    
    # Read the file content as UTF-8
    try:
        with open(resolved_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        raise ValueError("File encoding is not UTF-8")
    except PermissionError:
        raise ValueError("Permission denied")
