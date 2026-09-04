import os

def read_report(filename: str, reports_root: str) -> str:
    reports_root = os.path.realpath(reports_root)
    
    if not os.path.isdir(reports_root):
        raise ValueError("disallowed")
    
    candidate = os.path.normpath(os.path.join(reports_root, filename))
    
    parts = filename.replace('\\', '/').split('/')
    current = reports_root
    for part in parts:
        if part == '' or part == '.':
            continue
        if part == '..':
            current = os.path.dirname(current)
            continue
        current = os.path.join(current, part)
        if os.path.islink(current):
            raise ValueError("disallowed")
    
    resolved = os.path.realpath(candidate)
    
    if not resolved.startswith(reports_root + os.sep) and resolved != reports_root:
        raise ValueError("disallowed")
    
    if not os.path.isfile(resolved):
        raise FileNotFoundError(f"No such file: {resolved}")
    
    if os.path.islink(candidate):
        raise ValueError("disallowed")
    
    with open(resolved, 'r', encoding='utf-8') as f:
        return f.read()
