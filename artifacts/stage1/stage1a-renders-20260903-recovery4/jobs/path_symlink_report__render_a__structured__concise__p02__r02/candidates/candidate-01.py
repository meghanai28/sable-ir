import os

def read_report(filename: str, reports_root: str) -> str:
    reports_root = os.path.realpath(reports_root)
    
    if not os.path.isdir(reports_root):
        raise ValueError("disallowed")
    
    candidate_path = os.path.join(reports_root, filename)
    
    normalized_candidate = os.path.normpath(candidate_path)
    
    if not normalized_candidate.startswith(reports_root + os.sep) and normalized_candidate != reports_root:
        if not normalized_candidate.startswith(reports_root):
            raise ValueError("disallowed")
    
    current = reports_root
    remaining = filename
    
    if os.path.isabs(remaining):
        remaining = os.path.relpath(remaining, '/')
    
    parts = remaining.split(os.sep) if remaining else []
    
    for part in parts:
        if part == '' or part == '.':
            continue
        if part == '..':
            current = os.path.dirname(current)
            continue
        
        current = os.path.join(current, part)
        
        if os.path.islink(current):
            raise ValueError("disallowed")
    
    resolved_path = os.path.realpath(candidate_path)
    
    if not resolved_path.startswith(reports_root + os.sep) and resolved_path != reports_root:
        if not resolved_path.startswith(reports_root):
            raise ValueError("disallowed")
    
    if not os.path.isfile(resolved_path):
        if not os.path.exists(resolved_path):
            raise FileNotFoundError(f"No such file: '{resolved_path}'")
        raise ValueError("disallowed")
    
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
