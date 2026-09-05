import os

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    Propagates FileNotFoundError for a missing ordinary file and raises ValueError
    when the request is disallowed (e.g., absolute paths, path traversal, or symlinks escaping root).
    """
    # Normalize the root to an absolute path to ensure consistent handling
    resolved_root = os.path.abspath(reports_root)
    
    # Check if filename is absolute; if so, it escapes the intended root
    if os.path.isabs(filename):
        raise ValueError("Absolute filenames are not allowed")
    
    # Construct the candidate path by joining root and filename
    candidate_path = os.path.join(resolved_root, filename)
    
    # Normalize the candidate path to resolve '..' and '.' segments
    normalized_path = os.path.normpath(candidate_path)
    
    # Ensure the normalized path is still within the resolved root
    # This check must use os.path.commonpath or similar logic, but the safest way
    # is to ensure the normalized path starts with the root + separator or equals the root.
    if not (normalized_path == resolved_root or normalized_path.startswith(resolved_root + os.sep)):
        raise ValueError("Path traversal detected")
    
    # Resolve the complete target path, following symbolic links
    resolved_target = os.path.realpath(normalized_path)
    
    # Ensure the resolved target (after symlink resolution) is still inside reports_root
    if not (resolved_target == resolved_root or resolved_target.startswith(resolved_root + os.sep)):
        raise ValueError("Symbolic link escapes the reports root")
    
    # Check if the resolved path is an ordinary file (not a directory, not a symlink to a dir, etc.)
    if not os.path.isfile(resolved_target):
        raise FileNotFoundError(f"The file {resolved_target} does not exist or is not a regular file")
    
    # Read and return the UTF-8 text
    with open(resolved_target, 'r', encoding='utf-8') as f:
        return f.read()
