import os

def read_report(filename: str, reports_root: str) -> str:
    # Normalize reports_root to absolute canonical path
    canonical_root = os.path.realpath(os.path.abspath(reports_root))
    
    # Join filename to reports_root and canonicalize
    joined_path = os.path.join(reports_root, filename)
    canonical_path = os.path.realpath(os.path.abspath(joined_path))
    
    # Verify containment under reports_root (strictly inside)
    if not canonical_path.startswith(canonical_root + os.sep) and canonical_path != canonical_root:
        raise ValueError("Path traversal outside reports_root")
    
    # Verify no user-selected path component is a symlink
    # Split filename into components and check each path segment from reports_root down
    if filename:
        # Get the relative path from reports_root to canonical_path
        try:
            rel_path = os.path.relpath(canonical_path, canonical_root)
        except ValueError:
            raise ValueError("Path traversal outside reports_root")
        
        if rel_path.startswith('..'):
            raise ValueError("Path traversal outside reports_root")
        
        # Check each component in the user-provided filename for symlinks
        current_path = canonical_root
        # Use the original filename components to trace the path
        for component in filename.replace('\\', '/').split('/'):
            if component == '' or component == '.':
                continue
            if component == '..':
                # Go up one level in canonical path
                current_path = os.path.dirname(current_path)
                continue
            
            next_path = os.path.join(current_path, component)
            # Check if the component itself is a symlink
            if os.path.islink(next_path):
                raise ValueError("Symbolic link in path")
            
            current_path = os.path.realpath(next_path)
    
    # Verify the target is an ordinary file
    if not os.path.isfile(canonical_path):
        if not os.path.exists(canonical_path):
            raise FileNotFoundError(f"File not found: {canonical_path}")
        raise ValueError("Target is not an ordinary file")
    
    # Open and read UTF-8 content
    with open(canonical_path, 'r', encoding='utf-8') as f:
        return f.read()
