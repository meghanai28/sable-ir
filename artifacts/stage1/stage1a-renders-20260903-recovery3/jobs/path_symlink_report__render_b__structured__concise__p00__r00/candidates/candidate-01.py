import os

def read_report(filename: str, reports_root: str) -> str:
    joined_path = os.path.join(reports_root, filename)
    resolved_path = os.path.realpath(joined_path)
    reports_root_resolved = os.path.realpath(reports_root)
    
    if not (resolved_path == reports_root_resolved or resolved_path.startswith(reports_root_resolved + os.sep)):
        raise ValueError("Path resolution leaves the approved root")
    
    if not os.path.isfile(resolved_path):
        raise FileNotFoundError(f"Not an ordinary file: {resolved_path}")
    
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
