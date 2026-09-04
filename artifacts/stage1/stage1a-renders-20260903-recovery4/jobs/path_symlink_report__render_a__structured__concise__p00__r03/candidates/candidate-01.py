import os


def read_report(filename: str, reports_root: str) -> str:
    # Step 1: Join filename to reports_root and resolve to an absolute path
    reports_root = os.path.abspath(reports_root)
    resolved_path = os.path.abspath(os.path.join(reports_root, filename))
    
    # Step 2: Validate the resolved path remains strictly inside reports_root
    if not (resolved_path == reports_root or resolved_path.startswith(reports_root + os.sep)):
        raise ValueError("Path escapes reports_root")
    
    # Step 3: Check each user-selected path component for symlink status and reject if present
    # Split the filename into user-selected components
    user_components = filename.replace('\\', '/').split('/')
    # Remove empty components (from leading/trailing slashes or multiple slashes)
    user_components = [c for c in user_components if c]
    
    current_path = reports_root
    for component in user_components:
        current_path = os.path.join(current_path, component)
        # Check if this path component is a symlink
        if os.path.islink(current_path):
            raise ValueError("Symlink encountered in path")
    
    # Step 4: Verify the target exists as an ordinary file
    if not os.path.exists(resolved_path):
        raise FileNotFoundError(f"File not found: {resolved_path}")
    if not os.path.isfile(resolved_path):
        raise ValueError("Target is not an ordinary file")
    
    # Step 5: Open in UTF-8 text mode and read contents
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
