import os
import pathlib

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    Propagate FileNotFoundError for a missing ordinary file and raise ValueError
    when the request is disallowed (path escapes root or symlink escapes root).
    """
    root_path = pathlib.Path(reports_root).resolve()
    target_path = pathlib.Path(filename).resolve()
    
    # Check if the filename is absolute or contains .. segments that might escape
    if target_path.is_absolute() or '..' in str(target_path).split(os.sep):
        # Resolve the target path
        resolved_target = target_path.resolve()
        
        # Check if the resolved target is within the reports_root
        try:
            resolved_target.relative_to(root_path)
        except ValueError:
            raise ValueError(f"Path {filename} escapes reports_root")
        
        # Check if the resolved target is a symlink and if its target is within reports_root
        if resolved_path.is_symlink():
            try:
                resolved_target.relative_to(root_path)
            except ValueError:
                raise ValueError(f"Symlink target for {filename} escapes reports_root")
    
    # Check if the file exists and is a regular file
    if not resolved_path.exists() or not resolved_path.is_file():
        raise FileNotFoundError(f"File {filename} not found")
    
    # Read the file content
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
