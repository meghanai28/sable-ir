import os

def read_report(filename: str, reports_root: str) -> str:
    joined_path = os.path.join(reports_root, filename)
    resolved_path = os.path.realpath(joined_path)
    resolved_root = os.path.realpath(reports_root)
    
    if not resolved_path.startswith(resolved_root + os.sep) and resolved_path != resolved_root:
        raise ValueError("Request escapes reports_root directory")
    
    with open(resolved_path, encoding="utf-8") as f:
        return f.read()
