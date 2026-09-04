import os
import pathlib

def read_report(filename: str, reports_root: str) -> str:
    # 1) Canonicalize `reports_root` to an absolute path.
    canonical_root = os.path.realpath(os.path.abspath(reports_root))
    
    # 2) Build the candidate path by joining the untrusted `filename` with the canonical root.
    candidate_path = os.path.join(canonical_root, filename)
    
    # 3) Resolve the candidate path fully through all symbolic links to produce a canonical absolute target path.
    resolved_target = os.path.realpath(candidate_path)
    
    # 4) Validate that the resolved target remains inside the canonical `reports_root`; raise `ValueError` if the boundary is violated.
    # Strict containment check: root must be a proper prefix of the resolved path
    if not (resolved_target.startswith(canonical_root + os.sep) or resolved_target == canonical_root):
        raise ValueError("Request disallowed: path escapes the approved root")
    
    # 5) Confirm the resolved target exists and is an ordinary file; raise `FileNotFoundError` otherwise.
    if not os.path.isfile(resolved_target):
        raise FileNotFoundError(f"Not an ordinary file: {resolved_target}")
    
    # 6) Open the validated path for reading and decode the raw bytes as UTF-8 to return the report string.
    with open(resolved_target, 'r', encoding='utf-8') as f:
        return f.read()
