import os

def read_report(filename: str, reports_root: str) -> str:
    reports_root = os.path.abspath(os.path.realpath(reports_root))
    
    joined_path = os.path.join(reports_root, filename)
    normalized_joined = os.path.normpath(joined_path)
    
    if not normalized_joined.startswith(reports_root + os.sep) and normalized_joined != reports_root:
        raise ValueError("Path escapes reports_root")
    
    resolved_path = os.path.realpath(normalized_joined)
    
    if not resolved_path.startswith(reports_root + os.sep) and resolved_path != reports_root:
        raise ValueError("Resolved symlink target escapes reports_root")
    
    if not os.path.isfile(resolved_path):
        raise FileNotFoundError(f"Not a file: {resolved_path}")
    
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
