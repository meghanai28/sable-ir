import os

def read_report(filename: str, reports_root: str) -> str:
    reports_root = os.path.abspath(os.path.realpath(reports_root))
    target_path = os.path.join(reports_root, filename)
    resolved_path = os.path.abspath(target_path)
    
    if not (
        resolved_path == reports_root or
        resolved_path.startswith(reports_root + os.sep)
    ):
        raise ValueError("Path traversal attempt detected")
    
    current = resolved_path
    while current != reports_root:
        if os.path.islink(current):
            raise ValueError("Symlink detected in path")
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    
    with open(resolved_path, encoding="utf-8") as f:
        return f.read()
