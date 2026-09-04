import os

def read_report(filename: str, reports_root: str) -> str:
    joined_path = os.path.join(reports_root, filename)
    real_path = os.path.realpath(joined_path)
    real_reports_root = os.path.realpath(reports_root)
    
    if not real_path.startswith(real_reports_root + os.sep) and real_path != real_reports_root:
        raise ValueError("Request disallowed: path escapes reports_root")
    
    if not os.path.isfile(real_path):
        if not os.path.exists(real_path):
            raise FileNotFoundError(f"No such file: {real_path}")
        raise ValueError("Request disallowed: target is not an ordinary file")
    
    with open(real_path, 'r', encoding='utf-8') as f:
        return f.read()
