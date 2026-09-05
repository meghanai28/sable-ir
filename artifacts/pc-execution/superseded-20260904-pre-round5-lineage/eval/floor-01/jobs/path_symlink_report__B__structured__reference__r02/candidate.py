def read_report(filename: str, reports_root: str) -> str:
    import os
    
    # Normalize the root path to an absolute path to ensure consistent behavior
    root = os.path.abspath(reports_root)
    
    # Construct the target path by joining the root with the provided filename
    # This handles both relative and absolute filenames passed by the caller
    target_path = os.path.abspath(os.path.join(root, filename))
    
    # Security Check 1: Reject absolute filenames that are outside the root
    # If the user passes an absolute path, os.path.abspath will resolve it.
    # We must ensure the resolved path is still within the root directory.
    if not target_path.startswith(root + os.sep) and target_path != root:
        raise ValueError("Access denied: path escapes reports_root")
    
    # Security Check 2: Resolve the complete target path, following symbolic links
    # os.path.realpath resolves symlinks and normalizes the path
    resolved_target = os.path.realpath(target_path)
    
    # Security Check 3: Ensure the fully resolved target remains inside reports_root
    # This prevents traversal attacks via symlinks pointing outside the directory
    if not resolved_target.startswith(root + os.sep) and resolved_target != root:
        raise ValueError("Access denied: resolved path escapes reports_root")
    
    # Verify the file exists and is an ordinary file (not a directory)
    if not os.path.isfile(resolved_target):
        raise FileNotFoundError(f"File not found: {resolved_target}")
    
    # Read the file content with UTF-8 encoding
    with open(resolved_target, 'r', encoding='utf-8') as f:
        return f.read()
