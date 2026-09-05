import os

def read_report(filename: str, reports_root: str) -> str:
    resolved_root = os.path.realpath(reports_root)
    resolved_filename = os.path.realpath(filename)
    resolved_path = os.path.realpath(os.path.join(resolved_root, resolved_filename))
    if not resolved_path.startswith(resolved_root):
        raise ValueError("Path escapes reports_root")
    if not os.path.isfile(resolved_path):
        raise FileNotFoundError
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
