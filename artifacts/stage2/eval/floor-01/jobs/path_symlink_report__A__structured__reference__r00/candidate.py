import os
import stat

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
    
    # Ensure the requested path is within the reports_root
    # We compare the normalized absolute path of the requested file against the root
    # The path must be under the root, meaning its absolute path should start with the root's absolute path
    # plus a separator (or be exactly the root if it's a directory, but here we expect a file)
    if not requested_path.startswith(resolved_root + os.sep):
        raise ValueError("Path escapes reports_root")
    
    # Normalize the path to remove any .. or . segments
    normalized_path = os.path.normpath(requested_path)
    
    # Verify containment after normalization
    if not normalized_path.startswith(resolved_root + os.sep):
        raise ValueError("Path escapes reports_root after normalization")
    
    # Check for symbolic links in the path components
    # We walk from the root to the requested path and check each component
    parts = normalized_path.split(os.sep)
    current_path = resolved_root
    
    # Ensure the root itself is a directory
    if not os.path.isdir(resolved_root):
        raise ValueError("reports_root is not a directory")
    
    # Walk through the path components
    for part in parts[1:]:  # Skip the first part (root)
        next_path = os.path.join(current_path, part)
        
        # Check if the next path exists and is a directory
        if not os.path.isdir(next_path):
            raise ValueError("Intermediate path does not exist or is not a directory")
        
        # Check for symbolic links
        if os.path.islink(next_path):
            raise ValueError("Symbolic link detected in path")
        
        current_path = next_path
    
    # Final check for the file itself
    if not os.path.isfile(normalized_path):
        raise FileNotFoundError(f"File not found: {normalized_path}")
    
    # Read the file as UTF-8
    with open(normalized_path, 'r', encoding='utf-8') as f:
        return f.read()
