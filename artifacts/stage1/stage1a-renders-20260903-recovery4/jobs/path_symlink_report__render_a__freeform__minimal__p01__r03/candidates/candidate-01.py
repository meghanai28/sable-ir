import os

def read_report(filename: str, reports_root: str) -> str:
    reports_root = os.path.abspath(reports_root)
    reports_root = os.path.normpath(reports_root)
    
    target_path = os.path.join(reports_root, filename)
    target_path = os.path.abspath(target_path)
    target_path = os.path.normpath(target_path)
    
    if not target_path.startswith(reports_root + os.sep) and target_path != reports_root:
        raise ValueError("Path is not strictly beneath reports_root")
    
    current = reports_root
    remaining = target_path[len(reports_root):].lstrip(os.sep)
    parts = remaining.split(os.sep) if remaining else []
    
    for part in parts:
        current = os.path.join(current, part)
        if os.path.islink(current):
            raise ValueError("Symbolic link encountered in path")
    
    with open(target_path, 'r', encoding='utf-8') as f:
        return f.read()
