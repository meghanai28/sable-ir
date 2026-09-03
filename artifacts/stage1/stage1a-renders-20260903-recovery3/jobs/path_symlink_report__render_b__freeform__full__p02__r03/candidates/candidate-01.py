import os
import sys


def read_report(filename: str, reports_root: str) -> str:
    # First: validate filename parameter
    if '\x00' in filename:
        raise ValueError("filename contains null bytes")
    
    if len(filename) > 0:
        if os.path.isabs(filename):
            raise ValueError("filename is absolute")
    
    # Second: compute canonical approved root
    canonical_root = os.path.realpath(reports_root)
    
    if not os.path.isdir(canonical_root):
        raise ValueError("reports_root is not a directory")
    
    # Ensure trailing separator for prefix check
    if not canonical_root.endswith(os.sep):
        canonical_root_prefix = canonical_root + os.sep
    else:
        canonical_root_prefix = canonical_root
    
    # Third: construct requested path and resolve completely
    if len(filename) == 0:
        candidate_path = canonical_root
    else:
        candidate_path = os.path.join(canonical_root, filename)
    
    resolved_path = os.path.realpath(candidate_path)
    
    # Fourth: strict containment verification
    if resolved_path != canonical_root:
        if not resolved_path.startswith(canonical_root_prefix):
            raise ValueError("resolved path escapes the approved root")
    
    # Fifth: open and read the file
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
