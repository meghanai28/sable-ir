import os

def read_report(filename: str, reports_root: str) -> str:
    resolved_root = os.path.abspath(reports_root)
    resolved_filename = os.path.abspath(filename)
    normalized_filename = os.path.normpath(resolved_filename)
    if not normalized_filename.startswith(resolved_root + os.sep) and normalized_filename != resolved_root:
        raise ValueError("Access denied")
    if os.path.islink(normalized_filename):
        raise ValueError("Symbolic link not allowed")
    if not os.path.isfile(normalized_filename):
        raise FileNotFoundError()
    with open(normalized_filename, 'r', encoding='utf-8') as f:
        return f.read()
