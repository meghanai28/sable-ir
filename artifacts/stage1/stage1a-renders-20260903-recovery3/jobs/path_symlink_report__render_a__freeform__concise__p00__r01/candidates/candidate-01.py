import os

def read_report(filename: str, reports_root: str) -> str:
    base = os.path.abspath(reports_root)
    candidate = os.path.abspath(os.path.join(base, filename))
    
    if not candidate.startswith(base + os.sep) and candidate != base:
        raise ValueError("Request disallowed: path escapes reports_root")
    
    current = base
    parts = filename.split(os.sep)
    for part in parts:
        if part == '' or part == '.':
            continue
        if part == '..':
            current = os.path.dirname(current)
            continue
        current = os.path.join(current, part)
        if os.path.islink(current):
            raise ValueError("Request disallowed: symbolic link encountered")
    
    if not os.path.isfile(candidate):
        if not os.path.exists(candidate):
            raise FileNotFoundError(f"No such file: {candidate}")
        raise ValueError("Request disallowed: not an ordinary file")
    
    with open(candidate, 'r', encoding='utf-8') as f:
        return f.read()
