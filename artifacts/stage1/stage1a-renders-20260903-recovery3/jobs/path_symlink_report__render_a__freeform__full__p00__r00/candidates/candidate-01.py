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
    
    # Join to reports_root and get absolute paths for containment check
    candidate_path = os.path.join(reports_root, normalized_filename)
    abs_reports_root = os.path.abspath(reports_root)
    abs_candidate = os.path.abspath(candidate_path)
    
    # Verify strict containment within reports_root
    # Add trailing separator to root to prevent prefix attacks (e.g., /root vs /root2)
    root_with_sep = abs_reports_root + os.sep
    if not (abs_candidate == abs_reports_root or abs_candidate.startswith(root_with_sep)):
        raise ValueError("Path escapes the approved root directory")
    
    # Component-wise walk checking for symbolic links
    current_path = abs_reports_root
    # Check if reports_root itself is a symlink (policy applies to user-selected components,
    # but we also need to verify the walk path)
    for segment in normalized_parts:
        current_path = os.path.join(current_path, segment)
        # Use lstat to check without following symlinks
        try:
            st = os.lstat(current_path)
        except FileNotFoundError:
            # Component doesn't exist, let the final open handle this
            # But we need to check parent directories that do exist
            # If we're at an intermediate point, the final open will fail
            # Continue to check remaining components that might exist
            continue
        
        # Check if this path component is a symbolic link
        if os.path.islink(current_path):
            raise ValueError("Symbolic link detected in path")
    
    # Re-verify containment after normalization (defense in depth)
    abs_final = os.path.abspath(current_path)
    if not (abs_final == abs_reports_root or abs_final.startswith(root_with_sep)):
        raise ValueError("Path escapes the approved root directory")
    
    # Open and read the file
    with open(abs_candidate, 'r', encoding='utf-8') as f:
        return f.read()
