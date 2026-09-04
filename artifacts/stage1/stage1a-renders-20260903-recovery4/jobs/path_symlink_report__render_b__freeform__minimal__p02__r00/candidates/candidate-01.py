import os

def read_report(filename: str, reports_root: str) -> str:
    abs_reports_root = os.path.abspath(reports_root)
    real_reports_root = os.path.realpath(abs_reports_root)
    
    joined_path = os.path.join(real_reports_root, filename)
    real_target = os.path.realpath(joined_path)
    
    if not real_target.startswith(real_reports_root + os.sep) and real_target != real_reports_root:
        raise ValueError("Request escapes reports_root")
    
    with open(real_target, 'r', encoding='utf-8') as f:
        return f.read()
