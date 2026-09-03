import os

def read_report(filename: str, reports_root: str) -> str:
    reports_root = os.path.abspath(os.path.realpath(reports_root))
    target_path = os.path.abspath(os.path.join(reports_root, filename))
    normalized_path = os.path.normpath(target_path)
    
    if not normalized_path.startswith(reports_root + os.sep) and normalized_path != reports_root:
        raise ValueError("Path is not strictly beneath reports_root")
    
    current = reports_root
    parts = filename.split(os.sep)
    for part in parts:
        if part == '' or part == '.':
            continue
        if part == '..':
            current = os.path.dirname(current)
            continue
        current = os.path.join(current, part)
        if os.path.islink(current):
            raise ValueError("Symbolic link detected in path")
    
    with open(normalized_path, 'r', encoding='utf-8') as f:
        return f.read()
