import os

def read_report(filename: str, reports_root: str) -> str:
    # Normalize reports_root to absolute canonical path
    canonical_root = os.path.realpath(os.path.abspath(reports_root))
    
    # Join filename to reports_root
    joined_path = os.path.join(canonical_root, filename)
    
    # Canonicalize the joined path
    canonical_path = os.path.realpath(joined_path)
    
    # Verify containment under reports_root (strictly inside)
    if not canonical_path.startswith(canonical_root + os.sep) and canonical_path != canonical_root:
        raise ValueError("Path traversal outside reports_root")
    
    # Verify no user-selected path component is a symlink
    # Check each component from the root down to the final path
    current_path = canonical_root
    # Split the relative path from root
    rel_path = os.path.relpath(canonical_path, canonical_root)
    if rel_path == '.':
        raise ValueError("Cannot read reports_root itself")
    
    components = rel_path.split(os.sep)
    for component in components:
        current_path = os.path.join(current_path, component)
        # Check if this specific path component (as joined) is a symlink
        if os.path.islink(current_path):
            raise ValueError("Symbolic link in path")
    
    # Verify the target is an ordinary file
    if not os.path.isfile(canonical_path):
        if not os.path.exists(canonical_path):
            raise FileNotFoundError(f"File not found: {canonical_path}")
        raise ValueError("Target is not an ordinary file")
    
    # Open and read UTF-8 content
    with open(canonical_path, 'r', encoding='utf-8') as f:
        return f.read()
