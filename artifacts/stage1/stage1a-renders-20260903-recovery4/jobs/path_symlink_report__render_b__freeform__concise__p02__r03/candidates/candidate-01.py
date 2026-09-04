import os

def read_report(filename: str, reports_root: str) -> str:
    resolved_root = os.path.realpath(os.path.abspath(reports_root))
    candidate = os.path.join(resolved_root, filename)
    resolved_target = os.path.realpath(os.path.abspath(candidate))
    
    if not (resolved_target == resolved_root or resolved_target.startswith(resolved_root + os.sep)):
        raise ValueError("Request disallowed: path escapes reports_root")
    
    with open(resolved_target, encoding="utf-8") as f:
        return f.read()
