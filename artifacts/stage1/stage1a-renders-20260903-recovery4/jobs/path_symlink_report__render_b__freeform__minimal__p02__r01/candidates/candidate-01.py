import os

def read_report(filename: str, reports_root: str) -> str:
    resolved_root = os.path.realpath(os.path.abspath(reports_root))
    target_path = os.path.join(resolved_root, filename)
    resolved_target = os.path.realpath(target_path)
    
    if not resolved_target.startswith(resolved_root + os.sep) and resolved_target != resolved_root:
        raise ValueError("Request escapes reports_root")
    
    with open(resolved_target, encoding="utf-8") as f:
        return f.read()
