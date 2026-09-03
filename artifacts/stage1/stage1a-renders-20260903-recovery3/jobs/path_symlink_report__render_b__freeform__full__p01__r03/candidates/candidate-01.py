import os

def read_report(filename: str, reports_root: str) -> str:
    resolved_root = os.path.realpath(reports_root)
    
    candidate = os.path.join(resolved_root, filename)
    
    resolved_target = os.path.realpath(candidate)
    
    common = os.path.commonpath([resolved_target, resolved_root])
    if common != resolved_root or resolved_target == resolved_root:
        raise ValueError("Request disallowed: path escapes the approved root boundary")
    
    with open(resolved_target, encoding='utf-8') as f:
        return f.read()
