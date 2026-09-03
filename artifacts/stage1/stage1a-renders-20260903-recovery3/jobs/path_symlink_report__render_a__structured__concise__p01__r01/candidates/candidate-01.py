import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    reports_root = os.path.abspath(reports_root)
    
    if os.path.isabs(filename):
        user_components = []
        remaining = filename
        while remaining != os.path.sep:
            remaining, tail = os.path.split(remaining)
            if tail:
                user_components.insert(0, tail)
            elif remaining == os.path.sep:
                break
    else:
        user_components = filename.split(os.path.sep)
        user_components = [c for c in user_components if c != '']
    
    for i, component in enumerate(user_components):
        if component == '.' or component == '..':
            continue
        
        current_path = os.path.join(reports_root, *user_components[:i+1])
        current_path = os.path.normpath(current_path)
        
        if os.path.islink(current_path):
            raise ValueError("Symlink detected in user path")
    
    target_path = os.path.join(reports_root, *user_components)
    target_path = os.path.normpath(target_path)
    
    resolved_path = os.path.realpath(target_path)
    
    if not resolved_path.startswith(reports_root + os.path.sep) and resolved_path != reports_root:
        raise ValueError("Path traversal outside reports_root")
    
    if not os.path.exists(resolved_path):
        raise FileNotFoundError(f"File not found: {filename}")
    
    if not os.path.isfile(resolved_path):
        raise ValueError("Target is not an ordinary file")
    
    if stat.S_ISLNK(os.lstat(resolved_path).st_mode):
        raise ValueError("Symlink detected in user path")
    
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
