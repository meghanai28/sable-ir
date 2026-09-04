import os

def read_report(filename: str, reports_root: str) -> str:
    reports_root = os.path.abspath(reports_root)
    requested_path = os.path.abspath(os.path.join(reports_root, filename))
    
    if not requested_path.startswith(reports_root + os.sep) and requested_path != reports_root:
        raise ValueError("Request is disallowed")
    
    if not os.path.isfile(requested_path):
        raise FileNotFoundError(f"File not found: {requested_path}")
    
    with open(requested_path, 'r', encoding='utf-8') as f:
        return f.read()
