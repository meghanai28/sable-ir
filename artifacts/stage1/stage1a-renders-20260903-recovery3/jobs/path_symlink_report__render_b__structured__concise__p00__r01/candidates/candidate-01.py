import os
import pathlib

def read_report(filename: str, reports_root: str) -> str:
    reports_root_path = pathlib.Path(reports_root).resolve()
    target_path = (reports_root_path / filename).resolve()
    
    try:
        target_path.relative_to(reports_root_path)
    except ValueError:
        raise ValueError("Path resolution leaves the approved root")
    
    if target_path.is_symlink():
        raise ValueError("Symbolic link target leaves the approved root")
    
    if not target_path.is_file():
        raise FileNotFoundError(f"Not an ordinary file: {target_path}")
    
    with open(target_path, 'r', encoding='utf-8') as f:
        return f.read()
