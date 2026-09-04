import os

def read_report(filename: str, reports_root: str) -> str:
    joined_path = os.path.join(reports_root, filename)
    resolved_path = os.path.realpath(joined_path)
    resolved_root = os.path.realpath(reports_root)
    
    if not resolved_path.startswith(resolved_root + os.sep) and resolved_path != resolved_root:
        raise ValueError("Request disallowed: path escapes reports_root")
    
    if not os.path.isfile(resolved_path):
        raise FileNotFoundError(f"Not an ordinary file: {resolved_path}")
    
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
