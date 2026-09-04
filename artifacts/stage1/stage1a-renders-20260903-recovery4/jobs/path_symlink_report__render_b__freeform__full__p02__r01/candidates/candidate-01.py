import os


def read_report(filename: str, reports_root: str) -> str:
    if '\x00' in filename:
        raise ValueError("filename contains null bytes")
    
    if os.path.isabs(filename):
        raise ValueError("filename must be relative")
    
    canonical_root = os.path.realpath(reports_root)
    if not canonical_root.endswith(os.sep):
        canonical_root_prefix = canonical_root + os.sep
    else:
        canonical_root_prefix = canonical_root
    
    candidate_path = os.path.join(canonical_root, filename)
    resolved_path = os.path.realpath(candidate_path)
    
    if resolved_path != canonical_root and not resolved_path.startswith(canonical_root_prefix):
        raise ValueError("resolved path escapes the approved root")
    
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
