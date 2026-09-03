import os

def read_report(filename: str, reports_root: str) -> str:
    reports_root = os.path.abspath(reports_root)
    
    if not os.path.isdir(reports_root):
        raise ValueError("reports_root must be a directory")
    
    filename = filename.lstrip('/')
    
    if os.path.isabs(filename):
        raise ValueError("absolute paths are not allowed")
    
    components = filename.split(os.sep)
    
    if not components or components == ['']:
        raise ValueError("empty filename")
    
    if '..' in components:
        raise ValueError("directory traversal is not allowed")
    
    current_path = reports_root
    for component in components[:-1]:
        current_path = os.path.join(current_path, component)
        if os.path.islink(current_path):
            raise ValueError("symbolic link in user path")
        if not os.path.isdir(current_path):
            raise FileNotFoundError(f"No such directory: {current_path}")
    
    final_path = os.path.join(current_path, components[-1])
    
    if os.path.islink(final_path):
        raise ValueError("symbolic link in user path")
    
    resolved_path = os.path.realpath(final_path)
    
    if not resolved_path.startswith(reports_root + os.sep) and resolved_path != reports_root:
        raise ValueError("path escapes reports_root")
    
    if not os.path.exists(final_path):
        raise FileNotFoundError(f"No such file: {final_path}")
    
    if not os.path.isfile(final_path):
        raise ValueError("target is not an ordinary file")
    
    with open(final_path, 'r', encoding='utf-8') as f:
        return f.read()
