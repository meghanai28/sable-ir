import os

def read_report(filename: str, reports_root: str) -> str:
    resolved_root = os.path.realpath(os.path.abspath(reports_root))
    target_path = os.path.realpath(os.path.abspath(os.path.join(resolved_root, filename)))
    
    if not target_path.startswith(resolved_root + os.sep) and target_path != resolved_root:
        raise ValueError("Request disallowed: path escapes reports_root")
    
    with open(target_path, encoding="utf-8") as f:
        return f.read()
