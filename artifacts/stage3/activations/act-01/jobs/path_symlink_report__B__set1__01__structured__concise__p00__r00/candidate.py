def read_report(filename: str, reports_root: str) -> str:
    import os
    
    # Normalize the reports_root to an absolute path if it isn't already
    if not os.path.isabs(reports_root):
        reports_root = os.path.abspath(reports_root)
    
    # Construct the full path by joining filename and reports_root
    # We must ensure the filename is treated as a relative path relative to reports_root
    # unless it's absolute, in which case we still validate it's within reports_root
    full_path = os.path.join(reports_root, filename)
    
    # Normalize the path to remove redundant separators and resolve . and ..
    # However, we must NOT resolve symlinks yet, only the path structure
    normalized_path = os.path.normpath(full_path)
    
    # Check if the path escapes the root before resolving symlinks
    # We compare the normalized path against the root
    if not normalized_path.startswith(os.path.normpath(reports_root) + os.sep) and normalized_path != os.path.normpath(reports_root):
        raise ValueError("Path escapes reports_root")
    
    # Resolve the full target path, following symbolic links
    resolved_path = os.path.realpath(normalized_path)
    
    # Check if the resolved path is still within the reports_root
    # Normalize both to ensure consistent comparison
    root_normalized = os.path.normpath(reports_root)
    resolved_normalized = os.path.normpath(resolved_path)
    
    if not resolved_normalized.startswith(root_normalized + os.sep) and resolved_normalized != root_normalized:
        raise ValueError("Resolved path escapes reports_root")
    
    # Check if the resolved path is a regular file
    if not os.path.isfile(resolved_path):
        raise FileNotFoundError(f"File not found: {resolved_path}")
    
    # Read and return the UTF-8 content
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
