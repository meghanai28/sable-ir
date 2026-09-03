import os

def read_report(filename: str, reports_root: str) -> str:
    reports_root = os.path.realpath(reports_root)
    candidate = os.path.normpath(os.path.join(reports_root, filename))
    
    if not candidate.startswith(reports_root + os.sep) and candidate != reports_root:
        raise ValueError("directory traversal detected")
    
    current = reports_root
    remaining = filename.lstrip(os.sep)
    parts = remaining.split(os.sep) if remaining else []
    
    for part in parts:
        if part == '' or part == '.':
            continue
        if part == '..':
            raise ValueError("directory traversal detected")
        current = os.path.join(current, part)
        if os.path.islink(current):
            raise ValueError("symbolic link detected")
    
    if not candidate.startswith(reports_root + os.sep) and candidate != reports_root:
        raise ValueError("directory traversal detected")
    
    with open(candidate, 'r', encoding='utf-8') as f:
        return f.read()
