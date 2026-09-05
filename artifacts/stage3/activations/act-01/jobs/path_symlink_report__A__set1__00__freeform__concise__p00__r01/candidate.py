import os

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    Propagate FileNotFoundError for a missing ordinary file and raise ValueError
    when the request is disallowed (e.g., path escapes root or contains symlinks).
    """
    # Resolve the root directory to an absolute path
    resolved_root = os.path.abspath(reports_root)
    
    # Normalize the requested filename to an absolute path
    requested_path = os.path.abspath(filename)
    
    # Check if the requested path is within the reports_root
    # Use os.path.commonpath to ensure the path is strictly under the root
    common = os.path.commonpath([resolved_root, requested_path])
    if common != resolved_root:
        raise ValueError("Requested path escapes the reports_root directory.")
    
    # Normalize the path to remove any .. segments and ensure it's relative to the root
    # We need to construct the full path and check for symlinks in the components
    full_path = os.path.abspath(os.path.join(resolved_root, filename))
    
    # Walk each user-selected path component beneath the resolved reports_root
    # and raise ValueError if any component is a symbolic link.
    # We split the path into components and check each one.
    parts = full_path.split(os.sep)
    current_path = resolved_root
    
    # Ensure we don't go above the root during traversal
    for part in parts:
        if part == '':
            continue
        current_path = os.path.join(current_path, part)
        # Check if the current component is a symbolic link
        if os.path.islink(current_path):
            raise ValueError("Symbolic link found in the path.")
    
    # Double-check the final path for symlinks
    if os.path.islink(full_path):
        raise ValueError("Symbolic link found in the final path.")
    
    # Check if the file exists and is a regular file
    if not os.path.isfile(full_path):
        raise FileNotFoundError(f"File not found: {full_path}")
    
    # Read and return the UTF-8 text of the validated report
    with open(full_path, 'r', encoding='utf-8') as f:
        return f.read()
