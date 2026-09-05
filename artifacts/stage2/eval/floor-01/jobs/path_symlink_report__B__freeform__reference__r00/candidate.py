import os

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Security measures:
    - Treat filename as untrusted input.
    - Normalize the requested path and raise ValueError if it escapes the resolved reports_root.
    - Resolve the complete target path, following symbolic links.
    - Raise ValueError unless the fully resolved target remains inside reports_root.
    - A symbolic link whose resolved target stays inside the root may be read.
    - Resolve and check containment before opening the file.
    - Let a missing ordinary file raise FileNotFoundError.
    - Return the UTF-8 text of the validated report only.
    """
    # Resolve the root directory to a canonical absolute path
    root_dir = os.path.realpath(reports_root)
    
    # Normalize the filename to prevent path traversal before joining
    # We use os.path.normpath to handle .. and . segments, but do not resolve symlinks yet
    normalized_filename = os.path.normpath(filename)
    
    # Construct the candidate path
    candidate_path = os.path.join(root_dir, normalized_filename)
    
    # Resolve the candidate path to catch path traversal attempts that might be
    # masked by normpath (though normpath is strong, realpath is the final check)
    # We must ensure the path does not escape the root directory
    if not candidate_path.startswith(root_dir + os.sep) and candidate_path != root_dir:
        # This check handles cases where normpath might not fully prevent traversal
        # or if the root is not a prefix in the normalized form
        raise ValueError("Path escapes reports_root")
    
    # Final resolution and containment check
    resolved_path = os.path.realpath(candidate_path)
    
    # Ensure the resolved path is still within the root directory
    # Using os.path.commonpath to verify containment safely
    try:
        common = os.path.commonpath([root_dir, resolved_path])
        if common != root_dir:
            raise ValueError("Resolved path escapes reports_root")
    except ValueError:
        raise ValueError("Invalid path structure")
    
    # Check if the resolved path is a file
    if not os.path.isfile(resolved_path):
        raise FileNotFoundError(f"The file {filename} does not exist")
    
    # Read and return the UTF-8 text
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
