import os

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    Propagates FileNotFoundError for a missing ordinary file and raises ValueError
    when the request is disallowed (e.g., path escapes root or is a symlink outside root).
    """
    # Resolve the root directory to an absolute path
    resolved_root = os.path.realpath(reports_root)
    
    # Construct the target path by joining the root and the filename
    # We do not use os.path.join directly for the final check if we want to handle
    # cases where filename is absolute, but the spec says "joined beneath reports_root".
    # However, if filename is absolute, joining it might not be safe without explicit checks.
    # The plan says "joined beneath reports_root", implying the filename is relative.
    # But we must treat filename as untrusted.
    # Let's construct the candidate path.
    candidate_path = os.path.join(reports_root, filename)
    
    # Normalize the candidate path to remove . and .. components
    # We use os.path.normpath which handles relative paths.
    normalized_candidate = os.path.normpath(candidate_path)
    
    # Check if the normalized candidate escapes the root
    # The resolved root should be a prefix of the normalized candidate
    if not (normalized_candidate.startswith(resolved_root + os.sep) or normalized_candidate == resolved_root):
        raise ValueError("Path escapes reports_root")
    
    # Resolve the complete target path, following symbolic links
    # We need to check the link target, not just the normalized path.
    # However, the plan says "resolve the complete target path, following symbolic links,
    # and raise ValueError unless the fully resolved target remains inside reports_root".
    # This implies we must resolve the link to check containment.
    
    try:
        resolved_target = os.path.realpath(normalized_candidate)
    except (OSError, ValueError):
        raise ValueError("Invalid path")
    
    # Check if the resolved target is inside reports_root
    if not (resolved_target.startswith(resolved_root + os.sep) or resolved_target == resolved_root):
        raise ValueError("Resolved target escapes reports_root")
    
    # Check if it's an ordinary file
    if not os.path.isfile(normalized_candidate):
        raise FileNotFoundError(f"The file {filename} does not exist")
    
    # Read the file
    with open(normalized_candidate, 'r', encoding='utf-8') as f:
        return f.read()
