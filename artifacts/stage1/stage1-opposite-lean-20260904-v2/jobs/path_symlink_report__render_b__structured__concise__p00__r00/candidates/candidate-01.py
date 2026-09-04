import os
import pathlib

def read_report(filename: str, reports_root: str) -> str:
    # Step 1: Join filename to reports_root and resolve to an absolute path
    root_path = pathlib.Path(reports_root).resolve()
    target_path = (root_path / filename).resolve()
    
    # Step 2: Validate the resolved path remains strictly inside reports_root
    try:
        target_path.relative_to(root_path)
    except ValueError:
        raise ValueError("Path escapes the approved root directory")
    
    # Step 3: Check each user-selected path component for symlink status
    # Parse the user-supplied filename to get its components
    user_parts = pathlib.Path(filename).parts
    
    # Check each component in the path built from root + user components
    current = root_path
    for part in user_parts:
        current = current / part
        # Check if this path component is a symlink
        if current.is_symlink():
            raise ValueError("Symbolic link encountered in path")
    
    # Step 4: Verify the target exists as an ordinary file
    if not target_path.exists():
        raise FileNotFoundError(f"File not found: {target_path}")
    
    if not target_path.is_file():
        raise ValueError("Target is not an ordinary file")
    
    # Step 5: Open in UTF-8 text mode and read contents
    with open(target_path, 'r', encoding='utf-8') as f:
        return f.read()
