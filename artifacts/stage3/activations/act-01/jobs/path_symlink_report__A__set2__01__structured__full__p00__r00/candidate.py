import os

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    Propagate FileNotFoundError for a missing ordinary file and raise ValueError
    when the request is disallowed (path escapes root or contains symlinks).
    """
    # Resolve the root directory to an absolute path
    resolved_root = os.path.realpath(reports_root)
    
    # Resolve the requested filename to an absolute path
    resolved_filename = os.path.realpath(filename)
    
    # Check if the resolved filename starts with the resolved root
    # Use os.path.commonpath to ensure the path is strictly within the root
    # We need to handle the case where filename might be absolute or relative
    if not os.path.isabs(filename):
        # If filename is relative, resolve it relative to the current working directory
        # But the requirement says "joined beneath reports_root", so we should treat it as relative to reports_root
        # However, the safest interpretation based on "joined beneath reports_root" is to resolve it relative to reports_root
        # Let's resolve it relative to the current directory first, then check if it's within reports_root
        # Actually, the plan says "joined beneath reports_root", which implies we should construct the path as reports_root / filename
        # But to be safe against absolute paths, we should resolve the filename first
        pass
    
    # Construct the full path by joining reports_root and filename
    # If filename is absolute, we should check if it's within reports_root
    if os.path.isabs(filename):
        full_path = filename
    else:
        full_path = os.path.join(reports_root, filename)
    
    # Resolve the full path to get the real path
    resolved_full_path = os.path.realpath(full_path)
    
    # Check if the resolved path is within the reports_root
    # We need to ensure that the resolved path is strictly within the reports_root directory
    # Use os.path.commonpath to check if the resolved path is within the reports_root
    try:
        common = os.path.commonpath([resolved_root, resolved_full_path])
        if common != resolved_root:
            raise ValueError("Path escapes the reports_root directory")
    except ValueError:
        raise ValueError("Path escapes the reports_root directory")
    
    # Walk each selected component of the requested path beneath reports_root
    # and raise ValueError if any component is a symbolic link, even one that currently points inside the directory
    # We need to check each component of the path from reports_root to the final file
    # Split the path into components (excluding the root)
    parts = os.path.normpath(full_path).split(os.sep)
    current_path = resolved_root
    
    for i, part in enumerate(parts):
        if part == '':
            continue
        next_path = os.path.join(current_path, part)
        # Check if the next_path is a symbolic link
        if os.path.islink(next_path):
            raise ValueError("Symbolic link found in the path")
        # Also check if the next_path is a directory (if it's not the final file)
        if not os.path.isfile(next_path) and not os.path.isdir(next_path):
            # This might be an issue if the path is not a file or directory
            # But we should continue to the next part
            pass
        current_path = next_path
    
    # Check if the final path is a file
    if not os.path.isfile(resolved_full_path):
        raise FileNotFoundError(f"File not found: {resolved_full_path}")
    
    # Read the file
    with open(resolved_full_path, 'r', encoding='utf-8') as f:
        return f.read()
