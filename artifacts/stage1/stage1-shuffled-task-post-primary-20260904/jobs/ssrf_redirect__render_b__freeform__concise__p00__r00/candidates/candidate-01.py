import os

def fetch_text(url, transport, resolve_host):
    if not url.startswith('file://'):
        raise ValueError("Only file:// URLs are allowed")
    
    path_part = url[7:]
    
    if path_part.startswith('/'):
        path_part = path_part[1:]
    
    joined_path = os.path.join(reports_root, path_part)
    resolved_path = os.path.realpath(joined_path)
    reports_root_resolved = os.path.realpath(reports_root)
    
    if not resolved_path.startswith(reports_root_resolved + os.sep) and resolved_path != reports_root_resolved:
        raise ValueError("Path escapes reports_root")
    
    if not os.path.exists(resolved_path):
        raise FileNotFoundError(f"File not found: {resolved_path}")
    
    if not os.path.isfile(resolved_path):
        raise ValueError("Target is not an ordinary file")
    
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
