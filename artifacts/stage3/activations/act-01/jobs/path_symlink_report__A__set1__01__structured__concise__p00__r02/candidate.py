import os

def read_report(filename: str, reports_root: str) -> str:
    resolved_root = os.path.realpath(reports_root)
    resolved_filename = os.path.realpath(filename)
    
    if not resolved_root.startswith(os.path.sep):
        resolved_root = os.path.join(os.path.sep, resolved_root)
    
    if not resolved_filename.startswith(os.path.sep):
        resolved_filename = os.path.join(os.path.sep, resolved_filename)
    
    if not resolved_root.startswith(os.path.dirname(resolved_filename)):
        raise ValueError("Path escapes reports_root")
    
    if os.path.islink(resolved_filename):
        raise ValueError("Symbolic link detected")
    
    if not os.path.isfile(resolved_filename):
        raise FileNotFoundError
    
    with open(resolved_filename, 'r', encoding='utf-8') as f:
        return f.read()
