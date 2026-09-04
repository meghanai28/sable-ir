import os


def read_report(filename: str, reports_root: str) -> str:
    # Lexically normalize filename without filesystem syscalls
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
    abs_candidate = os.path.abspath(candidate_path)
    abs_root = os.path.abspath(reports_root)
    
    # Ensure trailing separator for root to prevent prefix attacks
    if not abs_root.endswith(os.sep):
        abs_root_with_sep = abs_root + os.sep
    else:
        abs_root_with_sep = abs_root
    
    # Verify candidate is strictly contained within reports_root
    if abs_candidate == abs_root:
        raise ValueError("Path escapes root directory")
    
    if not (abs_candidate == abs_root or abs_candidate.startswith(abs_root_with_sep)):
        raise ValueError("Path escapes root directory")
    
    # Component-wise walk checking for symbolic links
    current_path = abs_root
    for segment in normalized_parts:
        current_path = os.path.join(current_path, segment)
        try:
            if os.path.islink(current_path):
                raise ValueError("Symbolic link detected")
        except OSError:
            # If we can't stat, let it fail later on open, or re-raise if it's a real error
            # But for islink, if the path doesn't exist, it returns False
            # So an OSError here is unusual; we'll let it propagate as needed
            pass
    
    # Open and read the file
    with open(current_path, 'r', encoding='utf-8') as f:
        return f.read()
