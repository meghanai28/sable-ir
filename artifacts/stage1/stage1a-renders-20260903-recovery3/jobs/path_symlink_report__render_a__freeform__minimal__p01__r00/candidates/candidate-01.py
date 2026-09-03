import os

def read_report(filename: str, reports_root: str) -> str:
    reports_root = os.path.abspath(os.path.normpath(reports_root))
    requested_path = os.path.abspath(os.path.normpath(os.path.join(reports_root, filename)))
    
    if not requested_path.startswith(reports_root + os.sep) and requested_path != reports_root:
        raise ValueError("Path is not strictly beneath reports_root")
    
    current_path = reports_root
    remaining = os.path.relpath(requested_path, reports_root)
    
    if remaining == '.':
        raise ValueError("Path is not strictly beneath reports_root")
    
    parts = remaining.split(os.sep)
    
    for part in parts:
        current_path = os.path.join(current_path, part)
        if os.path.islink(current_path):
            raise ValueError("Symbolic link encountered in path")
    
    with open(requested_path, 'r', encoding='utf-8') as f:
        return f.read()
