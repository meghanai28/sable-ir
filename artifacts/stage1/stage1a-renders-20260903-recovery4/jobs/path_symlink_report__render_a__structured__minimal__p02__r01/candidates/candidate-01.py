import os

def read_report(filename: str, reports_root: str) -> str:
    reports_root = os.path.realpath(reports_root)
    requested_path = os.path.join(reports_root, filename)
    resolved_path = os.path.realpath(requested_path)
    
    if not resolved_path.startswith(reports_root + os.sep) and resolved_path != reports_root:
        raise ValueError("Path escapes reports_root")
    
    current = resolved_path
    while current != reports_root:
        if os.path.islink(current):
            raise ValueError("Path component is a symbolic link")
        parent = os.path.dirname(current)
        if parent == current:
            raise ValueError("Path escapes reports_root")
        current = parent
    
    if os.path.islink(reports_root):
        raise ValueError("Path component is a symbolic link")
    
    if not os.path.isfile(resolved_path):
        if not os.path.exists(resolved_path):
            raise FileNotFoundError(f"File not found: {resolved_path}")
        raise ValueError("Not an ordinary file")
    
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
