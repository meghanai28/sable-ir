import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    Propagates FileNotFoundError for a missing ordinary file and raises ValueError when the request is disallowed.
    """
    target_path = os.path.join(reports_root, filename)
    
    # Validate the path is within the root
    real_root = os.path.realpath(reports_root)
    real_target = os.path.realpath(target_path)
    
    if not real_target.startswith(real_root + os.sep) and real_target != real_root:
        raise ValueError("Path is outside the approved filesystem root.")
    
    # Check if the path exists and is a file
    if not os.path.exists(target_path):
        raise FileNotFoundError(f"The file {filename} does not exist.")
    
    if not os.path.isfile(target_path):
        raise ValueError(f"The path {filename} is not an ordinary file.")
    
    # Security check: reject symbolic links
    if os.path.islink(target_path):
        raise ValueError("Symbolic links are not permitted.")
    
    # Read the file content
    with open(target_path, 'r', encoding='utf-8') as f:
        return f.read()
