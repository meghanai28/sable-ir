import os
import pathlib

def read_report(filename: str, reports_root: str) -> str:
    root_path = pathlib.Path(reports_root).resolve()
    
    normalized = os.path.normpath(filename)
    if os.path.isabs(normalized):
        raise ValueError("Absolute paths are not allowed")
    
    target_path = (root_path / normalized).resolve()
    
    if not _is_within_root(target_path, root_path):
        raise ValueError("Path escapes the approved root directory")
    
    if target_path.is_symlink():
        target_path = target_path.resolve()
        if not _is_within_root(target_path, root_path):
            raise ValueError("Symlink target escapes the approved root directory")
    
    if not target_path.exists():
        raise FileNotFoundError(f"File not found: {filename}")
    
    if not target_path.is_file():
        raise ValueError("Not an ordinary file")
    
    with open(target_path, 'r', encoding='utf-8') as f:
        return f.read()

def _is_within_root(path: pathlib.Path, root: pathlib.Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False
