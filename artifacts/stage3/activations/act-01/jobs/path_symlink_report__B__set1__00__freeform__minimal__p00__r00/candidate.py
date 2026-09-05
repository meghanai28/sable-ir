import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Args:
        filename: Untrusted input filename.
        reports_root: Directory containing valid reports.
    
    Returns:
        The UTF-8 text of the validated report.
    
    Raises:
        ValueError: If the path escapes reports_root or is a symbolic link outside the root.
        FileNotFoundError: If the file does not exist or is not a regular file.
    """
    # Normalize the root to an absolute path
    resolved_root = os.path.normpath(os.path.abspath(reports_root))
    
    # Join the filename with the root to get the requested path
    requested_path = os.path.normpath(os.path.join(resolved_root, filename))
    
    # Check if the requested path escapes the root (e.g., contains .. that goes above)
    # We need to ensure the requested path is within the root directory
    if not requested_path.startswith(resolved_root + os.sep) and requested_path != resolved_root:
        # This check handles cases where filename contains .. that escapes the root
        # Note: os.path.normpath might have already resolved .., so we check containment
        # A safer approach is to check if the normalized path is still within the root
        # But we must also handle the case where filename is absolute
        if os.path.isabs(filename):
            raise ValueError("Access denied: absolute path not allowed")
        # After normalization, check if it's outside the root
        # We need to be careful with .. segments that were resolved
        # The safest way is to check if the path starts with the root + separator or equals the root
        # However, if filename contains .., normpath might resolve it. We need to validate before resolving too much.
        # Let's re-evaluate: we normalize the path but then check if it's within root.
        # If filename has .. that goes above root, normpath will resolve it. We must detect this.
        # We can do this by checking if the original filename (or its normalized version) 
        # when joined with root results in a path that is not under root.
        # Actually, the requirement says "may be absolute, contain .. segments".
        # We should resolve the path after joining but before checking, and ensure it's within root.
        # But if we use normpath, .. segments are resolved. So we check containment after resolution.
        pass
    
    # Resolve the complete target path, following symbolic links
    # We need to check the link target, not just the requested path
    try:
        target_path = os.path.realpath(requested_path)
    except (OSError, ValueError):
        raise ValueError("Access denied: cannot resolve path")
    
    # Check if the resolved target is within the root
    # We must ensure the target is within the root directory
    if not target_path.startswith(resolved_root + os.sep) and target_path != resolved_root:
        raise ValueError("Access denied: path escapes reports_root")
    
    # Check if the file exists and is a regular file
    if not os.path.isfile(requested_path):
        raise FileNotFoundError(f"The file '{filename}' does not exist")
    
    # Read the file
    with open(requested_path, 'r', encoding='utf-8') as f:
        return f.read()
