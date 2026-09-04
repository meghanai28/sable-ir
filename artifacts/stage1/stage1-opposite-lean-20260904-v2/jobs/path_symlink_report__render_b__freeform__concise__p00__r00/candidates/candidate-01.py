import os

def read_report(filename: str, reports_root: str) -> str:
    base = os.path.abspath(reports_root)
    candidate = os.path.normpath(os.path.join(base, filename))
    
    if not candidate.startswith(base + os.sep) and candidate != base:
        raise ValueError("Request disallowed: path escapes reports_root")
    
    current = base
    parts = filename.replace('\\', '/').strip('/').split('/')
    parts = [p for p in parts if p and p != '.']
    
    for part in parts:
        current = os.path.join(current, part)
        if os.path.islink(current):
            raise ValueError("Request disallowed: symbolic link encountered")
    
    if not os.path.isfile(current):
        if not os.path.exists(current):
            raise FileNotFoundError(f"No such file: {current}")
        raise ValueError("Request disallowed: not an ordinary file")
    
    with open(current, 'r', encoding='utf-8') as f:
        return f.read()
