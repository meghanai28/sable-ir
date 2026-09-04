import os

def read_report(filename: str, reports_root: str) -> str:
    reports_root = os.path.abspath(os.path.realpath(reports_root))
    target_path = os.path.abspath(os.path.join(reports_root, filename))
    normalized_path = os.path.normpath(target_path)
    
    if not normalized_path.startswith(reports_root + os.sep) and normalized_path != reports_root:
        raise ValueError("Path is not strictly beneath reports_root")
    
    current = reports_root
    remaining = filename
    
    while remaining:
        remaining = os.path.normpath(remaining)
        if remaining == '.' or remaining == '':
            break
        
        if os.path.sep in remaining:
            part, remaining = remaining.split(os.path.sep, 1)
        else:
            part, remaining = remaining, ''
        
        if part == '' or part == '.':
            continue
        if part == '..':
            raise ValueError("Path traversal not allowed")
        
        current = os.path.join(current, part)
        
        if os.path.islink(current):
            raise ValueError("Symbolic link not allowed")
    
    with open(normalized_path, 'r', encoding='utf-8') as f:
        return f.read()
