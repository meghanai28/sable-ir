import os

def read_report(filename: str, reports_root: str) -> str:
    abs_reports_root = os.path.abspath(reports_root)
    real_reports_root = os.path.realpath(abs_reports_root)
    
    target_path = os.path.join(abs_reports_root, filename)
    real_target_path = os.path.realpath(target_path)
    
    if not real_target_path.startswith(real_reports_root + os.sep) and real_target_path != real_reports_root:
        raise ValueError("Request escapes reports_root")
    
    with open(real_target_path, encoding='utf-8') as f:
        return f.read()
