import os

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    Propagate FileNotFoundError for a missing ordinary file and raise ValueError
    when the request is disallowed (e.g., path traversal, symlinks, or escape).
    """
    # Resolve the root directory to a canonical absolute path to prevent symlink escapes
    root_canonical = os.path.realpath(reports_root)
    
    # Construct the target path
    target_path = os.path.join(reports_root, filename)
    
    # Normalize the path to remove .. and . components
    # We must ensure the normalized path does not escape the root
    normalized_target = os.path.normpath(target_path)
    
    # Check if the normalized path is outside the root directory
    if not normalized_target.startswith(root_canonical + os.sep) and normalized_target != root_canonical:
        raise ValueError("Path traversal detected")
    
    # Resolve the target path to check for symlinks
    # os.path.realpath resolves symlinks, so we can check if the resolved path is within the root
    resolved_target = os.path.realpath(normalized_target)
    
    # Check if the resolved target is within the root directory
    if not resolved_target.startswith(root_canonical + os.sep) and resolved_target != root_canonical:
        raise ValueError("Symbolic link escapes the reports root")
    
    # Check if the file exists and is a regular file
    if not os.path.isfile(normalized_target):
        raise FileNotFoundError(f"The file {filename} does not exist or is not a regular file")
    
    # Read the file content as UTF-8
    with open(normalized_target, 'r', encoding='utf-8') as f:
        return f.read()
