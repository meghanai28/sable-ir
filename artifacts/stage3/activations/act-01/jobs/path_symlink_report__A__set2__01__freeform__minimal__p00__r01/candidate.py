import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Args:
        filename: The name of the file to read (treated as untrusted input).
        reports_root: The root directory where the report should be located.
    
    Returns:
        The UTF-8 text of the validated report.
    
    Raises:
        ValueError: If the requested path escapes reports_root or contains symbolic links.
        FileNotFoundError: If the file does not exist or is not a regular file.
    """
    # Resolve the reports_root to an absolute path
    resolved_root = os.path.abspath(reports_root)
    
    # Join the filename with the root to get the target path
    target_path = os.path.join(resolved_root, filename)
    
    # Normalize the target path to remove any .. or . segments
    normalized_target = os.path.normpath(target_path)
    
    # Check if the normalized path escapes the resolved root
    # We need to ensure the normalized path is still within the root directory
    if not normalized_target.startswith(resolved_root + os.sep) and normalized_target != resolved_root:
        raise ValueError("Path escapes reports_root")
    
    # Check if the file exists
    if not os.path.exists(normalized_target):
        raise FileNotFoundError(f"The file {filename} does not exist")
    
    # Check if it's a regular file
    if not os.path.isfile(normalized_target):
        raise FileNotFoundError(f"{filename} is not a regular file")
    
    # Walk up the path components to check for symbolic links
    # We need to check each component from the root to the target
    parts = normalized_target.split(os.sep)
    current_path = resolved_root
    
    # Ensure we start at the root and check each part
    for part in parts:
        if part == '':
            continue
        current_path = os.path.join(current_path, part)
        # Check if the current path is a symbolic link
        if os.path.islink(current_path):
            raise ValueError(f"Symbolic link detected at {part}")
    
    # Read the file
    with open(normalized_target, 'r', encoding='utf-8') as f:
        return f.read()
