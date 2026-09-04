import os
import pathlib

def read_report(filename: str, reports_root: str) -> str:
    canonical_root = os.path.realpath(os.path.abspath(reports_root))
    
    combined_path = os.path.join(canonical_root, filename)
    
    resolved_path = os.path.realpath(combined_path)
    
    canonical_root_with_sep = canonical_root + os.sep
    
    if not (resolved_path.startswith(canonical_root_with_sep) and resolved_path != canonical_root):
        raise ValueError("Request disallowed: path escapes the approved root")
    
    with open(resolved_path, encoding='utf-8') as f:
        return f.read()
