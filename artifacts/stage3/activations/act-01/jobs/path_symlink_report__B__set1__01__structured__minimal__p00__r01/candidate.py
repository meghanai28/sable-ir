import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Args:
        filename: The requested file name/path.
        reports_root: The root directory for reports.
    
    Returns:
        The UTF-8 text content of the file.
    
    Raises:
        FileNotFoundError: If the file does not exist or is not a regular file.
        ValueError: If the resolved path escapes reports_root or is a directory.
    """
    # Resolve the root directory to an absolute path
    resolved_root = os.path.abspath(reports_root)
    
    # Normalize the requested filename
    requested_path = os.path.normpath(filename)
    
    # Construct the full path
    full_path = os.path.join(resolved_root, requested_path)
    
    # Normalize the full path to resolve any .. segments
    normalized_full_path = os.path.normpath(full_path)
    
    # Check if the path is absolute and escapes the root
    if not normalized_full_path.startswith(resolved_root + os.sep) and normalized_full_path != resolved_root:
        raise ValueError("Path escapes reports_root")
    
    # Get the file info to check if it's a regular file
    try:
        file_stat = os.stat(normalized_full_path)
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {filename}")
    
    # Check if it's a regular file (not a directory, symlink to directory, etc.)
    if not stat.S_ISREG(file_stat.st_mode):
        raise ValueError("Requested path is not a regular file")
    
    # Resolve the symlink target if it's a symlink
    # We need to ensure that even if it's a symlink, the resolved target is within reports_root
    if os.path.islink(normalized_full_path):
        resolved_link_target = os.path.realpath(normalized_full_path)
        # Check if the resolved target is within reports_root
        if not resolved_link_target.startswith(resolved_root + os.sep) and resolved_link_target != resolved_root:
            raise ValueError("Symbolic link target escapes reports_root")
    else:
        resolved_link_target = normalized_full_path
    
    # Final containment check
    if not resolved_link_target.startswith(resolved_root + os.sep) and resolved_link_target != resolved_root:
        raise ValueError("Resolved path escapes reports_root")
    
    # Read the file content
    with open(normalized_full_path, 'r', encoding='utf-8') as f:
        return f.read()
