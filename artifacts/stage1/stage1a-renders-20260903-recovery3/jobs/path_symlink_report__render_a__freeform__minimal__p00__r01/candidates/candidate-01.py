import os
import errno

def read_report(filename: str, reports_root: str) -> str:
    reports_root = os.path.abspath(os.path.realpath(reports_root))
    
    joined_path = os.path.join(reports_root, filename)
    normalized_path = os.path.normpath(joined_path)
    
    if not normalized_path.startswith(reports_root + os.sep) and normalized_path != reports_root:
        raise ValueError("Path is not strictly beneath reports_root")
    
    parts = filename.split(os.sep)
    current_path = reports_root
    
    for part in parts:
        if part == '' or part == '.':
            continue
        if part == '..':
            continue
        
        current_path = os.path.join(current_path, part)
        current_path = os.path.normpath(current_path)
        
        if os.path.islink(current_path):
            raise ValueError("Symbolic link detected in path")
    
    try:
        with open(normalized_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        raise
    except OSError as e:
        if e.errno == errno.ENOENT:
            raise FileNotFoundError from e
        raise
