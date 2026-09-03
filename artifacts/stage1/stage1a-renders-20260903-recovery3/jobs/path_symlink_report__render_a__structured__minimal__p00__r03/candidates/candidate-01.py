import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    reports_root = os.path.abspath(reports_root)
    
    candidate_path = os.path.join(reports_root, filename)
    candidate_path = os.path.normpath(candidate_path)
    
    if not candidate_path.startswith(reports_root + os.sep) and candidate_path != reports_root:
        raise ValueError("Path escapes reports_root")
    
    if not os.path.exists(candidate_path):
        raise FileNotFoundError(f"File not found: {candidate_path}")
    
    if not os.path.isfile(candidate_path):
        raise ValueError("Not an ordinary file")
    
    path_parts = filename.replace('\\', '/').split('/')
    current_path = reports_root
    for part in path_parts:
        if part == '' or part == '.':
            continue
        current_path = os.path.join(current_path, part)
        current_path = os.path.normpath(current_path)
        if os.path.islink(current_path):
            raise ValueError("Symbolic link detected in path")
    
    with open(candidate_path, 'rb') as f:
        raw_bytes = f.read()
    
    try:
        return raw_bytes.decode('utf-8')
    except UnicodeDecodeError as e:
        raise ValueError(f"Invalid UTF-8: {e}")
