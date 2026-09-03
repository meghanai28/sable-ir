import os

def read_report(filename: str, reports_root: str) -> str:
    reports_root = os.path.abspath(reports_root)
    target_path = os.path.abspath(os.path.join(reports_root, filename))
    normalized_target = os.path.normpath(target_path)
    
    if not normalized_target.startswith(reports_root + os.sep) and normalized_target != reports_root:
        raise ValueError("Path is not strictly beneath reports_root")
    
    current_path = reports_root
    remaining = normalized_target[len(reports_root):].lstrip(os.sep)
    segments = remaining.split(os.sep) if remaining else []
    
    for segment in segments:
        current_path = os.path.join(current_path, segment)
        if os.path.islink(current_path):
            raise ValueError("Symbolic link encountered in path")
    
    with open(normalized_target, 'r', encoding='utf-8') as f:
        return f.read()
