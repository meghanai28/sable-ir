import os

def read_report(filename: str, reports_root: str) -> str:
    reports_root = os.path.realpath(reports_root)
    
    if not os.path.isdir(reports_root):
        raise ValueError("disallowed")
    
    candidate = os.path.join(reports_root, filename)
    
    norm_candidate = os.path.normpath(candidate)
    if not norm_candidate.startswith(reports_root + os.sep) and norm_candidate != reports_root:
        raise ValueError("disallowed")
    
    current = reports_root
    remaining = filename
    
    if os.path.isabs(remaining):
        remaining = remaining.lstrip(os.sep)
        if os.altsep:
            remaining = remaining.lstrip(os.altsep)
    
    parts = remaining.split(os.sep) if os.sep in remaining else [remaining]
    if os.altsep:
        new_parts = []
        for part in parts:
            new_parts.extend(part.split(os.altsep))
        parts = new_parts
    
    for part in parts:
        if part == '' or part == '.':
            continue
        if part == '..':
            current = os.path.dirname(current)
            continue
        
        current = os.path.join(current, part)
        
        if os.path.islink(current):
            raise ValueError("disallowed")
    
    resolved = os.path.realpath(candidate)
    
    if not (resolved.startswith(reports_root + os.sep) or resolved == reports_root):
        raise ValueError("disallowed")
    
    if not os.path.isfile(resolved):
        raise FileNotFoundError(f"No such file: '{resolved}'")
    
    if os.path.islink(resolved):
        raise ValueError("disallowed")
    
    with open(resolved, 'r', encoding='utf-8') as f:
        return f.read()
