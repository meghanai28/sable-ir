import os

def read_report(filename: str, reports_root: str) -> str:
    # Join filename to reports_root
    joined_path = os.path.join(reports_root, filename)
    
    # Canonicalize the path
    canonical_path = os.path.realpath(joined_path)
    
    # Verify containment under reports_root
    reports_root_canonical = os.path.realpath(reports_root)
    if not canonical_path.startswith(reports_root_canonical + os.sep) and canonical_path != reports_root_canonical:
        raise ValueError("Path traversal outside reports_root")
    
    # Verify no user-selected path component is a symlink
    # Check each component from reports_root downward
    current_path = reports_root_canonical
    remaining_path = os.path.relpath(canonical_path, reports_root_canonical)
    path_parts = remaining_path.split(os.sep) if remaining_path != '.' else []
    
    for part in path_parts:
        current_path = os.path.join(current_path, part)
        # Check if this specific path component is a symlink
        if os.path.islink(current_path):
            raise ValueError("Symbolic link in path")
    
    # Verify target is an ordinary file
    if not os.path.isfile(canonical_path):
        raise ValueError("Target is not an ordinary file")
    
    # Open and read UTF-8 content
    with open(canonical_path, 'r', encoding='utf-8') as f:
        return f.read()
