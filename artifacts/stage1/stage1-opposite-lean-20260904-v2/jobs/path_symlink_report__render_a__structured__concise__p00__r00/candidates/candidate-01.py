import os
import pathlib

def read_report(filename: str, reports_root: str) -> str:
    reports_root_path = pathlib.Path(reports_root).resolve()
    joined_path = reports_root_path / filename
    resolved_path = joined_path.resolve()
    
    try:
        resolved_path.relative_to(reports_root_path)
    except ValueError:
        raise ValueError("Path resolution leaves the approved root")
    
    if resolved_path.is_symlink():
        raise ValueError("Symbolic link target leaves the approved root")
    
    if not resolved_path.is_file():
        raise FileNotFoundError(f"Not an ordinary file: {resolved_path}")
    
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
