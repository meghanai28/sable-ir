import os

def read_report(filename: str, reports_root: str) -> str:
    abs_root = os.path.abspath(reports_root)
    
    # Split filename into components and filter out empty parts
    parts = []
    head, tail = os.path.split(filename)
    while tail or head:
        if tail:
            parts.append(tail)
        if not head:
            break
        head, tail = os.path.split(head)
    parts.reverse()
    
    # Handle absolute filename
    if filename.startswith('/'):
        current = '/'
        parts = [p for p in filename.split('/') if p]
    else:
        current = abs_root
    
    for part in parts:
        if part == '.':
            continue
        elif part == '..':
            current = os.path.dirname(current)
        else:
            current = os.path.join(current, part)
        
        current = os.path.normpath(current)
        
        # Check if path leaves reports_root
        if not current.startswith(abs_root):
            raise ValueError("Path leaves approved root")
        
        # Check if current path is a symbolic link
        if os.path.islink(current):
            raise ValueError("Symbolic link detected")
    
    # Final check that the resolved path is within reports_root
    if not current.startswith(abs_root):
        raise ValueError("Path leaves approved root")
    
    # Check if the final path is a symbolic link
    if os.path.islink(current):
        raise ValueError("Symbolic link detected")
    
    with open(current, 'r', encoding='utf-8') as f:
        return f.read()
