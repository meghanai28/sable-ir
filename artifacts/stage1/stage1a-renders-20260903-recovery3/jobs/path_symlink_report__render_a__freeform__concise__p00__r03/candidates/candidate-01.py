import os

def read_report(filename: str, reports_root: str) -> str:
    base = os.path.abspath(reports_root)
    candidate = os.path.normpath(os.path.join(base, filename))
    
    if not candidate.startswith(base + os.sep) and candidate != base:
        raise ValueError("Path traversal detected")
    
    current = base
    parts = filename.replace('\\', '/').strip('/').split('/')
    if parts == ['']:
        parts = []
    
    for part in parts:
        current = os.path.join(current, part)
        if os.path.islink(current):
            raise ValueError("Symbolic link detected")
    
    if not os.path.isfile(current):
        if not os.path.exists(current):
            raise FileNotFoundError(f"No such file: {current}")
        raise ValueError("Not an ordinary file")
    
    with open(current, 'r', encoding='utf-8') as f:
        return f.read()
