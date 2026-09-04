import os

def read_report(filename: str, reports_root: str) -> str:
    base_path = os.path.abspath(reports_root)
    candidate_path = os.path.abspath(os.path.join(base_path, filename))
    
    if not candidate_path.startswith(base_path + os.sep) and candidate_path != base_path:
        raise ValueError("Request disallowed: path escapes reports_root")
    
    current = base_path
    parts = filename.split(os.sep)
    for part in parts:
        if part == '' or part == '.':
            continue
        if part == '..':
            raise ValueError("Request disallowed: path escapes reports_root")
        current = os.path.join(current, part)
        if os.path.islink(current):
            raise ValueError("Request disallowed: symbolic link encountered")
    
    if not os.path.isfile(candidate_path):
        if not os.path.exists(candidate_path):
            raise FileNotFoundError(f"No such file: {candidate_path}")
        else:
            raise ValueError("Request disallowed: not an ordinary file")
    
    with open(candidate_path, 'r', encoding='utf-8') as f:
        return f.read()
