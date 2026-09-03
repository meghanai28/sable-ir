import os

def read_report(filename: str, reports_root: str) -> str:
    reports_root = os.path.abspath(os.path.realpath(reports_root))
    candidate = os.path.abspath(os.path.join(reports_root, filename))
    
    if not candidate.startswith(reports_root + os.sep) and candidate != reports_root:
        raise ValueError("directory traversal detected")
    
    current = reports_root
    remaining = filename
    
    while remaining:
        remaining = remaining.lstrip(os.sep)
        if not remaining:
            break
        if os.sep in remaining:
            part, remaining = remaining.split(os.sep, 1)
        else:
            part = remaining
            remaining = ""
        
        current = os.path.join(current, part)
        
        if os.path.islink(current):
            raise ValueError("symbolic link detected")
    
    with open(candidate, encoding="utf-8") as f:
        return f.read()
