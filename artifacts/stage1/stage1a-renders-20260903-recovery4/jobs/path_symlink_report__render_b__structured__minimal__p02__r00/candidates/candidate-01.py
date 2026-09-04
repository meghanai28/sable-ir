import os


def read_report(filename: str, reports_root: str) -> str:
    target_path = os.path.join(reports_root, filename)
    resolved_target = os.path.realpath(target_path)
    resolved_root = os.path.realpath(reports_root)
    
    if not resolved_target.startswith(resolved_root + os.sep) and resolved_target != resolved_root:
        raise ValueError("Request disallowed: target path escapes reports_root")
    
    with open(resolved_target, 'r', encoding='utf-8') as f:
        return f.read()
