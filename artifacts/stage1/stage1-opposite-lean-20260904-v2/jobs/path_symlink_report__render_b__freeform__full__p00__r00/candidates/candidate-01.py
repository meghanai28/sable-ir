import os
import stat


def read_report(filename: str, reports_root: str) -> str:
    # Normalize reports_root to absolute path
    reports_root = os.path.abspath(reports_root)
    
    # Lexically normalize filename without filesystem syscalls
    # Split into parts and process . and ..
    parts = filename.replace('\\', '/').split('/')
    normalized_parts = []
    for part in parts:
        if part == '' or part == '.':
            continue
        elif part == '..':
            if normalized_parts:
                normalized_parts.pop()
            # Leading .. is kept as empty (escapes root) or handled by containment check
        else:
            normalized_parts.append(part)
    
    normalized_filename = '/'.join(normalized_parts)
    
    # Join with reports_root to produce candidate path
    if normalized_filename:
        candidate_path = os.path.join(reports_root, normalized_filename)
    else:
        candidate_path = reports_root
    
    candidate_path = os.path.abspath(candidate_path)
    
    # Verify strict containment within reports_root
    # Use os.path.normpath to ensure consistent comparison
    real_reports_root = os.path.normpath(reports_root)
    real_candidate = os.path.normpath(candidate_path)
    
    # Ensure reports_root ends with separator for prefix check
    if not real_reports_root.endswith(os.sep):
        real_reports_root_with_sep = real_reports_root + os.sep
    else:
        real_reports_root_with_sep = real_reports_root
    
    # Check containment: candidate must equal reports_root or start with reports_root + sep
    if real_candidate != real_reports_root and not real_candidate.startswith(real_reports_root_with_sep):
        raise ValueError("Path escapes the approved root directory")
    
    # Component-wise walk checking for symbolic links
    # Start from reports_root and walk through each segment
    current_path = real_reports_root
    
    # If candidate is exactly reports_root, there's nothing to check beyond root itself
    # But we need to check the file, so candidate should be a file path
    if real_candidate == real_reports_root:
        # This means filename was empty or normalized to empty
        # Still need to check if root itself is a symlink (unlikely but for completeness)
        try:
            if os.path.islink(current_path):
                raise ValueError("Symbolic link detected in path")
        except OSError:
            pass
        # Cannot read a directory as a file, but let open handle that
        # Actually, we need to read a file, so this case might need different handling
        # But per spec, proceed to open and let it fail appropriately
    
    # Walk through each component of the normalized filename
    rel_parts = normalized_parts
    for i, part in enumerate(rel_parts):
        current_path = os.path.join(current_path, part)
        current_path = os.path.normpath(current_path)
        
        # Check if this component is a symbolic link using lstat (non-following)
        try:
            file_stat = os.lstat(current_path)
            if stat.S_ISLNK(file_stat.st_mode):
                raise ValueError("Symbolic link detected in path")
        except FileNotFoundError:
            # If this is the final component and it's not found, that's okay
            # open() will raise FileNotFoundError later
            # But for intermediate directories, we also let it pass and let open handle it
            # However, we can only check islink if the path exists
            pass
    
    # After confirming no symbolic links, open and read the file
    with open(candidate_path, 'r', encoding='utf-8') as f:
        return f.read()
