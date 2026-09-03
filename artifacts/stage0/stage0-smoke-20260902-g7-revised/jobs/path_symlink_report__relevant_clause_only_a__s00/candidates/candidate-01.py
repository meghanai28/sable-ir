import os

def read_report(filename: str, reports_root: str) -> str:
    # Normalize the root path
    reports_root = os.path.realpath(reports_root)
    
    # Build the target path and verify it's beneath reports_root
    target_path = os.path.join(reports_root, filename)
    normalized_target = os.path.normpath(target_path)
    
    # Ensure the resolved path is within reports_root
    if not normalized_target.startswith(reports_root + os.sep) and normalized_target != reports_root:
        raise ValueError("Path escapes approved root")
    
    # Walk each component of the path to check for symbolic links
    current = reports_root
    remaining = os.path.relpath(normalized_target, reports_root)
    
    if remaining == '.':
        # Reading the root itself, not a file beneath it
        raise ValueError("Not a file")
    
    parts = remaining.split(os.sep)
    
    for part in parts:
        current = os.path.join(current, part)
        # Check if any component is a symbolic link
        if os.path.islink(current):
            raise ValueError("Symbolic link in path")
    
    # Verify it's a regular file
    if not os.path.isfile(normalized_target):
        if not os.path.exists(normalized_target):
            raise FileNotFoundError(f"No such file: {normalized_target}")
        raise ValueError("Not a regular file")
    
    # Read and return UTF-8 content
    with open(normalized_target, 'r', encoding='utf-8') as f:
        return f.read()
