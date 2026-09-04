import os
import pathlib


def read_report(filename: str, reports_root: str) -> str:
    canonical_root = os.path.realpath(reports_root)
    if canonical_root.endswith(os.sep):
        canonical_root = canonical_root.rstrip(os.sep)
    if not os.path.isdir(canonical_root):
        raise ValueError("reports_root is not a directory")
    
    if os.path.isabs(filename):
        raise ValueError("absolute filename not allowed")
    
    raw_path = os.path.join(canonical_root, filename)
    normalized_path = os.path.normpath(raw_path)
    
    def _is_strictly_beneath(path: str, root: str) -> bool:
        if path == root:
            return False
        if not path.startswith(root + os.sep):
            return False
        return True
    
    if not _is_strictly_beneath(normalized_path, canonical_root):
        raise ValueError("path traversal detected")
    
    resolved_path = os.path.realpath(normalized_path)
    
    if not _is_strictly_beneath(resolved_path, canonical_root):
        raise ValueError("symlink target outside approved root")
    
    with open(resolved_path, encoding='utf-8') as f:
        return f.read()
