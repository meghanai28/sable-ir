import os

def read_report(filename: str, reports_root: str) -> str:
    resolved_root = os.path.realpath(os.path.abspath(reports_root))
    requested_path = os.path.join(resolved_root, filename)
    resolved_path = os.path.realpath(requested_path)
    
    if not resolved_path.startswith(resolved_root + os.sep) and resolved_path != resolved_root:
        raise ValueError("Request disallowed: path escapes approved root")
    
    if not os.path.isfile(resolved_path):
        raise FileNotFoundError(f"Not an existing ordinary file: {resolved_path}")
    
    with open(resolved_path, "r", encoding="utf-8") as f:
        return f.read()
