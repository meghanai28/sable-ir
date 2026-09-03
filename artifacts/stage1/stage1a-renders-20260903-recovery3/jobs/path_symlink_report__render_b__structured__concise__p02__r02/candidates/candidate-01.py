import os
import pathlib

def read_report(filename: str, reports_root: str) -> str:
    root_path = pathlib.Path(reports_root).resolve()
    target_path = (root_path / filename).resolve()
    
    try:
        target_path.relative_to(root_path)
    except ValueError:
        raise ValueError("Resolved path escapes approved root")
    
    if not target_path.is_file():
        raise FileNotFoundError(f"No ordinary file at validated path: {target_path}")
    
    with open(target_path, 'r', encoding='utf-8') as f:
        return f.read()
