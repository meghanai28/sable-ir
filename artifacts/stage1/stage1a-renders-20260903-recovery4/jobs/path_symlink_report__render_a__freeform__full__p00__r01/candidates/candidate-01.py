import os

def read_report(filename: str, reports_root: str) -> str:
    # Normalize filename lexically without filesystem syscalls
    parts = filename.replace('\\', '/').split('/')
    normalized_parts = []
    for part in parts:
        if part == '' or part == '.':
            continue
        elif part == '..':
            if normalized_parts:
                normalized_parts.pop()
        else:
            normalized_parts.append(part)
    
    normalized_filename = '/'.join(normalized_parts)
    
    # Join with reports_root and get absolute paths
    candidate_path = os.path.join(reports_root, normalized_filename)
    candidate_path = os.path.realpath(candidate_path)
    abs_reports_root = os.path.realpath(reports_root)
    
    # Verify candidate is strictly contained within reports_root
    # Ensure candidate_path starts with abs_reports_root followed by separator or is exactly abs_reports_root
    if not (candidate_path == abs_reports_root or 
            candidate_path.startswith(abs_reports_root + os.sep)):
        raise ValueError("Path escapes the approved root directory")
    
    # Component-wise walk checking for symbolic links
    # Start from reports_root and walk through each segment of normalized_filename
    current_path = abs_reports_root
    
    # If normalized_filename is empty, we're just checking reports_root itself
    # But we need to check components of the filename, not the root
    for segment in normalized_parts:
        current_path = os.path.join(current_path, segment)
        
        # Use lstat-based check that does not follow symbolic links
        try:
            if os.path.islink(current_path):
                raise ValueError("Symbolic link detected in path")
        except FileNotFoundError:
            # Component doesn't exist yet, which is fine for intermediate dirs
            # But we need to check if a parent that does exist is a symlink
            # Actually, islink raises FileNotFoundError if path doesn't exist
            # We only care about existing paths that are symlinks
            pass
    
    # After confirming no symlinks, open and read the file
    # Use the original candidate path (with realpath resolved) for opening
    with open(candidate_path, 'r', encoding='utf-8') as f:
        return f.read()
