import os

def read_report(filename: str, reports_root: str) -> str:
    if not os.path.isabs(reports_root):
        reports_root = os.path.abspath(reports_root)
    
    joined_path = os.path.join(reports_root, filename)
    canonical_path = os.path.realpath(joined_path)
    
    if not canonical_path.startswith(os.path.join(reports_root, '')) and canonical_path != reports_root:
        raise ValueError("Path traversal outside reports_root")
    
    if not os.path.exists(canonical_path):
        raise FileNotFoundError(f"File not found: {canonical_path}")
    
    if not os.path.isfile(canonical_path):
        raise ValueError("Target is not an ordinary file")
    
    user_parts = filename.replace('\\', '/').split('/')
    current = reports_root
    for part in user_parts:
        if part == '' or part == '.':
            continue
        if part == '..':
            current = os.path.dirname(current)
            continue
        current = os.path.join(current, part)
        current = os.path.realpath(current)
        if os.path.islink(current):
            raise ValueError("Symbolic link in user-selected path components")
    
    with open(canonical_path, 'r', encoding='utf-8') as f:
        return f.read()
