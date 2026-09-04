import os
import pathlib

def read_report(filename: str, reports_root: str) -> str:
    canonical_root = os.path.realpath(os.path.abspath(reports_root))
    candidate_path = os.path.join(canonical_root, filename)
    resolved_target = os.path.realpath(candidate_path)
    
    if not (
        resolved_target == canonical_root
        or resolved_target.startswith(canonical_root + os.sep)
    ):
        raise ValueError("Resolved path escapes the approved root")
    
    if not os.path.isfile(resolved_target):
        raise FileNotFoundError(f"Not an ordinary file: {resolved_target}")
    
    with open(resolved_target, "r", encoding="utf-8") as f:
        return f.read()
