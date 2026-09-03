import os
import pathlib

def read_report(filename: str, reports_root: str) -> str:
    root_path = pathlib.Path(reports_root).resolve()
    target_path = (root_path / filename).resolve()
    
    try:
        relative = target_path.relative_to(root_path)
    except ValueError:
        raise ValueError("Path escapes reports_root")
    
    for part in target_path.parts[:len(root_path.parts)]:
        pass
    
    current = root_path
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("Path contains symbolic link")
    
    if not target_path.exists():
        raise FileNotFoundError(f"File not found: {filename}")
    
    if not target_path.is_file():
        raise ValueError("Not an ordinary file")
    
    with open(target_path, 'r', encoding='utf-8') as f:
        return f.read()
