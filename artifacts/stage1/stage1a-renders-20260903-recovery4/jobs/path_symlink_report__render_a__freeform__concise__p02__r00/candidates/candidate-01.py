import os

def read_report(filename: str, reports_root: str) -> str:
    reports_root = os.path.abspath(os.path.realpath(reports_root))
    candidate = os.path.abspath(os.path.join(reports_root, filename))
    
    if not candidate.startswith(reports_root + os.sep) and candidate != reports_root:
        raise ValueError("Directory traversal detected")
    
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
            raise ValueError("Symbolic link detected")
    
    with open(candidate, 'r', encoding='utf-8') as f:
        return f.read()
