import os

def read_report(filename: str, reports_root: str) -> str:
    reports_root = os.path.realpath(reports_root)
    
    normalized = os.path.normpath(os.path.join(reports_root, filename))
    
    resolved = _resolve_with_containment(normalized, reports_root)
    
    if not _is_inside(resolved, reports_root):
        raise ValueError("Request escapes approved root")
    
    if not os.path.isfile(resolved):
        if not os.path.exists(resolved):
            raise FileNotFoundError(f"No such file: {resolved}")
        raise ValueError("Not an ordinary file")
    
    with open(resolved, 'r', encoding='utf-8') as f:
        return f.read()

def _resolve_with_containment(path: str, reports_root: str) -> str:
    parts = []
    current = path
    seen = set()
    
    while True:
        if current in seen:
            raise ValueError("Symlink loop detected")
        seen.add(current)
        
        parent, name = os.path.split(current)
        
        if name == '' or parent == current:
            parts.append(name)
            break
        
        if os.path.islink(current):
            target = os.readlink(current)
            if not os.path.isabs(target):
                target = os.path.join(parent, target)
            current = _resolve_with_containment(os.path.realpath(target), reports_root)
            if not _is_inside(current, reports_root):
                raise ValueError("Symlink target escapes approved root")
            return current
        
        parts.append(name)
        current = parent
    
    resolved = os.path.sep
    for part in reversed(parts):
        resolved = os.path.join(resolved, part)
    
    resolved = os.path.normpath(resolved)
    if resolved == '':
        resolved = os.path.sep
    
    return resolved

def _is_inside(path: str, root: str) -> bool:
    real_path = os.path.realpath(path)
    real_root = os.path.realpath(root)
    
    if real_path == real_root:
        return True
    
    prefix = real_root
    if not prefix.endswith(os.path.sep):
        prefix += os.path.sep
    
    return real_path.startswith(prefix) or real_path == real_root
