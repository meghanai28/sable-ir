import os

def read_report(filename: str, reports_root: str) -> str:
    member_path = os.path.join(reports_root, filename)
    abs_member_path = os.path.abspath(member_path)
    abs_reports_root = os.path.abspath(reports_root)
    
    if not abs_member_path.startswith(abs_reports_root + os.sep) and abs_member_path != abs_reports_root:
        raise ValueError("Request disallowed: path escapes reports_root")
    
    if not os.path.exists(abs_member_path):
        raise FileNotFoundError(f"File not found: {abs_member_path}")
    
    if os.path.islink(abs_member_path):
        raise ValueError("Request disallowed: symbolic links not permitted")
    
    if not os.path.isfile(abs_member_path):
        raise ValueError("Request disallowed: not a regular file")
    
    with open(abs_member_path, 'r', encoding='utf-8') as f:
        return f.read()
