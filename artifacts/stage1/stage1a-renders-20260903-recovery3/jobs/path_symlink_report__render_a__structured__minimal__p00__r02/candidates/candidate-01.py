import os

def read_report(filename: str, reports_root: str) -> str:
    reports_root = os.path.abspath(reports_root)
    candidate = os.path.join(reports_root, filename)
    candidate = os.path.abspath(candidate)
    
    if not candidate.startswith(reports_root + os.sep) and candidate != reports_root:
        raise ValueError("Path escapes reports_root")
    
    if not os.path.exists(candidate):
        raise FileNotFoundError(candidate)
    
    if not os.path.isfile(candidate):
        raise ValueError("Not an ordinary file")
    
    for part in candidate[len(reports_root):].split(os.sep):
        if part == '':
            continue
        check_path = os.path.join(reports_root, part)
        if os.path.islink(check_path):
            raise ValueError("Path component is a symbolic link")
    
    current = reports_root
    for part in candidate[len(reports_root):].split(os.sep):
        if part == '':
            continue
        current = os.path.join(current, part)
        if os.path.islink(current):
            raise ValueError("Path component is a symbolic link")
    
    with open(candidate, 'rb') as f:
        data = f.read()
    
    return data.decode('utf-8')
