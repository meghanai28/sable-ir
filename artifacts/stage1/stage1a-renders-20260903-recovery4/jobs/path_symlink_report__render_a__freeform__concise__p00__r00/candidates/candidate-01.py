import os

def read_report(filename: str, reports_root: str) -> str:
    base = os.path.abspath(reports_root)
    candidate = os.path.abspath(os.path.join(base, filename))
    
    if not candidate.startswith(base + os.sep) and candidate != base:
        raise ValueError("Path traversal attempt detected")
    
    current = base
    parts = filename.replace('\\', '/').strip('/').split('/')
    parts = [p for p in parts if p and p != '.']
    
    for part in parts:
        current = os.path.join(current, part)
        if os.path.islink(current):
            raise ValueError("Symbolic link detected in path")
    
    if not os.path.isfile(candidate):
        raise FileNotFoundError(f"Not an ordinary file: {candidate}")
    
    with open(candidate, 'r', encoding='utf-8') as f:
        return f.read()
