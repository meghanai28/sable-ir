def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Args:
        filename: The name of the file to read (untrusted input).
        reports_root: The root directory where reports are stored.
    
    Returns:
        The content of the report as a UTF-8 string.
    
    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the resolved path escapes reports_root or is disallowed.
    """
    import os
    import os.path
    
    # Resolve the canonical path for reports_root to ensure we're working with the real directory
    # and to handle any symlinks in the reports_root itself.
    canonical_root = os.path.realpath(reports_root)
    
    # Construct the full path by joining reports_root and filename
    # We use os.path.join to handle path separators correctly
    full_path = os.path.join(reports_root, filename)
    
    # Resolve the canonical path for the requested file, following symlinks
    # This is crucial for the GUARD requirement: "resolve the entire path, following symbolic links"
    canonical_file_path = os.path.realpath(full_path)
    
    # Check if the resolved path is within the canonical root
    # os.path.commonpath might not work perfectly with all OS-specific path separators in all cases,
    # so we use a more robust check: the canonical_file_path must start with the canonical_root + os.sep
    # or be exactly equal to canonical_root (if filename was empty, though that's invalid for a file).
    
    # Normalize the root to ensure it ends with a separator for comparison if needed, 
    # but the standard way is to check if the file path starts with the root path.
    # We must ensure the check is strict: the resolved path must be inside the root.
    
    # Check for directory traversal or escape attempts
    # The resolved path (canonical_file_path) must start with the resolved root (canonical_root)
    # followed by a separator, or be exactly the root (which shouldn't happen for a file).
    # However, os.path.realpath returns the absolute path.
    
    # A robust check:
    # 1. Ensure canonical_root ends with a separator if we are going to prepend, but better to use commonpath.
    # 2. Use os.path.commonpath to get the common prefix. If the common path is not the root, it escapes.
    
    common_path = os.path.commonpath([canonical_root, canonical_file_path])
    
    if common_path != canonical_root:
        raise ValueError("Path escapes reports_root")
    
    # Check if the file exists and is an ordinary file
    if not os.path.isfile(canonical_file_path):
        raise FileNotFoundError(f"The file {filename} does not exist")
    
    # Read the file with UTF-8 encoding
    try:
        with open(canonical_file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        raise
