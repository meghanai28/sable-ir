import os

def read_report(filename: str, reports_root: str) -> str:
    root_path = os.path.abspath(reports_root)
    target_path = os.path.join(root_path, filename)
    resolved_path = os.path.realpath(target_path)
    
    if not resolved_path.startswith(root_path + os.sep) and resolved_path != root_path:
        raise ValueError("Resolved path escapes the approved root")
    
    if not os.path.isfile(resolved_path):
        raise FileNotFoundError(f"Not an ordinary file: {resolved_path}")
    
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
