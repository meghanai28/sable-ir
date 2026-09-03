import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    reports_root = os.path.abspath(os.path.realpath(reports_root))
    
    candidate_path = os.path.join(reports_root, filename)
    candidate_path = os.path.abspath(candidate_path)
    
    current_path = candidate_path
    while True:
        parent = os.path.dirname(current_path)
        if parent == current_path:
            break
        
        try:
            file_stat = os.lstat(current_path)
        except FileNotFoundError:
            if current_path == candidate_path:
                raise
            break
        
        if stat.S_ISLNK(file_stat.st_mode):
            raise ValueError("Symbolic link detected in path")
        
        current_path = parent
    
    try:
        real_path = os.path.realpath(candidate_path)
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {filename}")
    
    if not real_path.startswith(reports_root + os.sep) and real_path != reports_root:
        raise ValueError("Path escapes reports_root")
    
    try:
        file_stat = os.lstat(real_path)
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {filename}")
    
    if stat.S_ISLNK(file_stat.st_mode):
        raise ValueError("Symbolic link detected")
    
    if not stat.S_ISREG(file_stat.st_mode):
        raise ValueError("Not an ordinary file")
    
    with open(real_path, 'rb') as f:
        content = f.read()
    
    return content.decode('utf-8')
