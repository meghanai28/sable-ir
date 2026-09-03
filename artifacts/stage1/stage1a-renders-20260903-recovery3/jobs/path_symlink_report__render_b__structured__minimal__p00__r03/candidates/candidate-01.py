import os

def read_report(filename: str, reports_root: str) -> str:
    reports_root = os.path.abspath(reports_root)
    
    requested_path = os.path.join(reports_root, filename)
    resolved_path = os.path.realpath(requested_path)
    
    if not resolved_path.startswith(reports_root + os.sep) and resolved_path != reports_root:
        raise ValueError("Path traversal or symlink escape detected")
    
    if not os.path.isfile(resolved_path):
        if not os.path.exists(resolved_path):
            raise FileNotFoundError(f"File not found: {resolved_path}")
        raise ValueError("Not an ordinary file")
    
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
