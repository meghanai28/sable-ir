import os

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Security measures:
    - Treats filename as untrusted input.
    - Normalizes paths to prevent directory traversal.
    - Resolves symbolic links and ensures the final target remains within reports_root.
    - Raises ValueError if the path escapes the root or if the request is disallowed.
    - Raises FileNotFoundError if the file is missing.
    - Returns the UTF-8 text of the validated report.
    """
    # Normalize the root directory to an absolute path
    resolved_root = os.path.normpath(os.path.abspath(reports_root))
    
    # Construct the candidate path by joining root and filename
    # This prevents path traversal attacks via .. in the input
    candidate_path = os.path.normpath(os.path.join(resolved_root, filename))
    
    # Check if the candidate path escapes the resolved root
    # We compare the normalized candidate with the root
    if not candidate_path.startswith(resolved_root + os.sep) and candidate_path != resolved_root:
        raise ValueError("Path escapes reports_root")
    
    # Resolve the complete target path, following symbolic links
    # We use os.path.realpath which resolves symlinks
    resolved_target = os.path.realpath(candidate_path)
    
    # Check if the resolved target remains inside reports_root
    # This prevents attacks where a symlink points outside the intended directory
    if not resolved_target.startswith(resolved_root + os.sep) and resolved_target != resolved_root:
        raise ValueError("Resolved target escapes reports_root")
    
    # Check if the resolved target is an ordinary file
    if not os.path.isfile(resolved_target):
        raise FileNotFoundError(f"File not found: {resolved_target}")
    
    # Read the file content
    with open(resolved_target, 'r', encoding='utf-8') as f:
        return f.read()
