import os

def read_report(filename: str, reports_root: str) -> str:
    reports_root = os.path.abspath(os.path.realpath(reports_root))
    
    candidate_path = os.path.join(reports_root, filename)
    candidate_path = os.path.abspath(candidate_path)
    
    # Check each path component for symlinks
    current = candidate_path
    while current != os.path.dirname(current):
        if os.path.islink(current):
            raise ValueError("Path contains symbolic link")
        current = os.path.dirname(current)
    
    # Also check the root itself isn't a symlink component in the path traversal
    # (already handled by walking up, but ensure we check the full path)
    if os.path.islink(candidate_path):
        raise ValueError("Path contains symbolic link")
    
    # Resolve the path to check for symlink traversal attacks
    resolved_path = os.path.realpath(candidate_path)
    
    # Check if resolved path is within reports_root
    if not (resolved_path == reports_root or resolved_path.startswith(reports_root + os.sep)):
        raise ValueError("Path escapes reports_root")
    
    # Check if it's an ordinary file
    if not os.path.isfile(candidate_path):
        raise FileNotFoundError(f"Not an ordinary file: {candidate_path}")
    
    # Read and decode
    with open(candidate_path, 'rb') as f:
        data = f.read()
    
    return data.decode('utf-8')
