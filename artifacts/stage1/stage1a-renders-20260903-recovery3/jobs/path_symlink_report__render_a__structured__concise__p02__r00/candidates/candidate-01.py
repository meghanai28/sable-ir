import os

def read_report(filename: str, reports_root: str) -> str:
    reports_root = os.path.realpath(reports_root)
    
    candidate_path = os.path.join(reports_root, filename)
    
    normalized_candidate = os.path.normpath(candidate_path)
    
    parts = filename.replace('\\', '/').split('/')
    parts = [p for p in parts if p]
    
    current_path = reports_root
    for part in parts:
        if part == '.' or part == '..':
            raise ValueError("Disallowed path component")
        
        next_path = os.path.join(current_path, part)
        
        if os.path.islink(next_path):
            raise ValueError("Symbolic link detected")
        
        current_path = next_path
    
    resolved_path = os.path.realpath(normalized_candidate)
    
    if not resolved_path.startswith(reports_root + os.sep) and resolved_path != reports_root:
        raise ValueError("Resolved path escapes reports_root")
    
    if not os.path.isfile(resolved_path):
        raise FileNotFoundError(f"Not a file: {resolved_path}")
    
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
