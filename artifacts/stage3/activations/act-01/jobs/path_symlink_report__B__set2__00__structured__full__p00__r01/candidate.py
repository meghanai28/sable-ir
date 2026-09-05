def read_report(filename: str, reports_root: str) -> str:
    import os
    import os.path
    
    # Normalize the root directory to an absolute path
    root_dir = os.path.abspath(reports_root)
    
    # Join the filename with the root directory
    full_path = os.path.abspath(os.path.join(root_dir, filename))
    
    # Resolve the full path, following symbolic links
    resolved_path = os.path.realpath(full_path)
    
    # Check if the resolved path is within the reports_root directory
    # We need to ensure the resolved path starts with the root directory path
    if not resolved_path.startswith(root_dir + os.sep) and resolved_path != root_dir:
        raise ValueError("Path escapes reports_root")
    
    # Check if the resolved path is a regular file
    if not os.path.isfile(resolved_path):
        raise FileNotFoundError(f"File not found: {filename}")
    
    # Read and return the UTF-8 content
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
