import os

def read_report(filename: str, reports_root: str) -> str:
    reports_root = os.path.abspath(reports_root)
    
    requested_path = os.path.join(reports_root, filename)
    requested_path = os.path.abspath(requested_path)
    
    if not requested_path.startswith(reports_root + os.sep) and requested_path != reports_root:
        raise ValueError("Request path escapes approved root")
    
    real_path = os.path.realpath(requested_path)
    
    if not real_path.startswith(reports_root + os.sep) and real_path != reports_root:
        raise ValueError("Resolved target escapes approved root")
    
    if not os.path.exists(real_path):
        raise FileNotFoundError(f"File not found: {filename}")
    
    if not os.path.isfile(real_path):
        raise ValueError("Not an ordinary file")
    
    with open(real_path, 'r', encoding='utf-8') as f:
        return f.read()
