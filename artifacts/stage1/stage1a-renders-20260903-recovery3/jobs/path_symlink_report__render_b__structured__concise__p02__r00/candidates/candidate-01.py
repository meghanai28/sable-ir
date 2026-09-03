import os

def read_report(filename: str, reports_root: str) -> str:
    reports_root = os.path.abspath(reports_root)
    target_path = os.path.join(reports_root, filename)
    resolved_path = os.path.realpath(target_path)
    
    if not resolved_path.startswith(reports_root + os.sep) and resolved_path != reports_root:
        raise ValueError("Resolved path escapes the approved root")
    
    if not os.path.isfile(resolved_path):
        raise FileNotFoundError(f"Not an ordinary file: {resolved_path}")
    
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
