import os

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    Propagates FileNotFoundError for a missing ordinary file and raises ValueError
    when the request is disallowed (path escape or symbolic link).
    """
    # Normalize the root directory to an absolute path to ensure consistent resolution
    resolved_root = os.path.abspath(reports_root)
    
    # Resolve the requested filename to an absolute path
    requested_path = os.path.abspath(filename)
    
    # Check if the resolved path escapes the root directory
    # We need to ensure the resolved path starts with the root path
    if not requested_path.startswith(resolved_root + os.sep) and requested_path != resolved_root:
        raise ValueError("Path escapes reports_root")
    
    # Walk through the path components to check for symbolic links
    # We split the path into components (excluding the root prefix)
    path_components = []
    current = requested_path[len(resolved_root):].lstrip(os.sep)
    
    # Handle the case where the path is exactly the root
    if not current:
        path_components = []
    else:
        # Split by separators, handling both / and \ if necessary, but os.path handles this
        # We manually split to get each component
        parts = current.split(os.sep)
        path_components = [p for p in parts if p]
    
    # Validate each component for symbolic links
    for component in path_components:
        full_component_path = os.path.join(resolved_root, *path_components[:path_components.index(component)+1])
        if os.path.islink(full_component_path):
            raise ValueError("Symbolic link detected in path")
    
    # Final check on the full path for symbolic links
    full_path = os.path.join(resolved_root, *path_components)
    if os.path.islink(full_path):
        raise ValueError("Symbolic link detected in final path")
    
    # Check if the file exists and is a regular file
    if not os.path.isfile(full_path):
        raise FileNotFoundError(f"File not found: {full_path}")
    
    # Read the file with UTF-8 encoding
    with open(full_path, 'r', encoding='utf-8') as f:
        return f.read()
