import os
import pathlib

def read_report(filename: str, reports_root: str) -> str:
    root_path = pathlib.Path(reports_root).resolve()
    target_path = (root_path / filename).resolve()
    
    try:
        target_path.relative_to(root_path)
    except ValueError:
        raise ValueError("Path escapes reports_root")
    
    if not target_path.exists():
        raise FileNotFoundError(f"File not found: {target_path}")
    
    if not target_path.is_file():
        raise ValueError("Target is not an ordinary file")
    
    current = target_path
    while current != root_path:
        if current.is_symlink():
            raise ValueError("Path contains symbolic link component")
        parent = current.parent
        if parent == current:
            break
        current = parent
    
    with open(target_path, 'r', encoding='utf-8') as f:
        return f.read()
