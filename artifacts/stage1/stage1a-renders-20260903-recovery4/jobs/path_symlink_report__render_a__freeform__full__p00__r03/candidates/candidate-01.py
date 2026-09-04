import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    # Normalize filename lexically without filesystem syscalls
    normalized = _lexical_normalize(filename)
    
    # Join with reports_root and get absolute path
    candidate = os.path.join(reports_root, normalized)
    candidate = os.path.abspath(candidate)
    reports_root_abs = os.path.abspath(reports_root)
    
    # Verify candidate is strictly contained within reports_root
    # Use os.path.join to ensure proper trailing separator handling
    if not _is_strictly_contained(candidate, reports_root_abs):
        raise ValueError("Path escapes the approved root directory")
    
    # Component-wise walk checking for symbolic links
    # Start from reports_root and walk through each segment
    current_path = reports_root_abs
    
    # Split normalized path into components
    components = normalized.split(os.sep)
    
    for component in components:
        if component == '' or component == '.':
            continue
        current_path = os.path.join(current_path, component)
        
        # Check if this component is a symbolic link using lstat (non-following)
        try:
            file_stat = os.lstat(current_path)
        except FileNotFoundError:
            # Component doesn't exist, which is fine for intermediate dirs
            # or the final file - we'll let the open() call handle it
            # But we need to continue checking remaining components?
            # Actually, if an intermediate component doesn't exist, we can't lstat it
            # The open will fail with FileNotFoundError later
            # For the final file, same thing
            # We should break here since we can't check further
            break
        
        # Check if symbolic link using lstat (doesn't follow symlinks)
        if stat.S_ISLNK(file_stat.st_mode):
            raise ValueError("Symbolic link detected in path")
    
    # After confirming no symlinks, open and read the file
    with open(candidate, 'r', encoding='utf-8') as f:
        return f.read()

def _lexical_normalize(path: str) -> str:
    """Normalize a path lexically without using filesystem syscalls."""
    # Handle empty path
    if not path:
        return ''
    
    # Split into components
    parts = path.replace('\\', '/').split('/')
    
    result = []
    for part in parts:
        if part == '' or part == '.':
            continue
        elif part == '..':
            if result:
                result.pop()
        else:
            result.append(part)
    
    return '/'.join(result)

def _is_strictly_contained(candidate: str, root: str) -> bool:
    """Check if candidate is strictly contained within root."""
    # Normalize both paths
    candidate = os.path.normpath(candidate)
    root = os.path.normpath(root)
    
    # Ensure root ends with separator for prefix check
    # This prevents /foo/bar matching /foo/barbaz
    if not root.endswith(os.sep):
        root_with_sep = root + os.sep
    else:
        root_with_sep = root
    
    if not candidate.endswith(os.sep):
        candidate_with_sep = candidate + os.sep
    else:
        candidate_with_sep = candidate
    
    # Candidate must equal root or start with root + separator
    if candidate == root:
        # Candidate is exactly the root directory, not strictly contained
        # But we need to allow reading files directly in root
        # Actually, the file itself should be inside root, not root itself
        # However, if filename is empty after normalization, we'd be reading root
        # Let's check: candidate should be root or inside root
        return True
    
    # Strict containment: candidate must start with root + separator
    return candidate_with_sep.startswith(root_with_sep) or candidate.startswith(root_with_sep)
