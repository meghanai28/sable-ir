import os

def read_report(filename: str, reports_root: str) -> str:
    # 1) Resolve reports_root to an absolute path and normalize it lexically.
    abs_reports_root = os.path.abspath(reports_root)
    norm_reports_root = os.path.normpath(abs_reports_root)
    
    # Ensure reports_root ends with separator for strict descendant check
    # We use os.path.join behavior, so we check with path separator logic
    
    # 2) Derive the normalized candidate absolute path by joining filename to reports_root and applying lexical normalization.
    joined_path = os.path.join(norm_reports_root, filename)
    candidate = os.path.normpath(joined_path)
    
    # 3) Execute the traversal validation; raise ValueError on failure.
    # Candidate must be a strict descendant of reports_root
    # Check: candidate starts with reports_root + os.sep, or handle edge cases
    if candidate == norm_reports_root:
        raise ValueError("Path equals reports_root, not a strict descendant")
    
    # For strict descendant check, ensure candidate is within reports_root
    # Add trailing separator to reports_root to prevent prefix attacks (e.g., /foo/bar matching /foo/baz)
    if not norm_reports_root.endswith(os.sep):
        reports_root_with_sep = norm_reports_root + os.sep
    else:
        reports_root_with_sep = norm_reports_root
    
    if not (candidate + os.sep).startswith(reports_root_with_sep):
        raise ValueError("Path escapes the approved filesystem boundary")
    
    # 4) Execute the symbolic-link validation by walking the raw components of filename
    current_path = norm_reports_root
    
    # Split filename on platform path separator
    components = filename.split(os.sep)
    
    for component in components:
        # Ignore empty components and '.'
        if component == '' or component == '.':
            continue
        
        if component == '..':
            # Step the logical current path up toward reports_root but never above it
            parent = os.path.dirname(current_path)
            # Ensure we don't go above reports_root
            if len(parent) < len(norm_reports_root):
                current_path = norm_reports_root
            else:
                # Check if parent is still within or equal to reports_root
                if parent == norm_reports_root or (parent + os.sep).startswith(reports_root_with_sep):
                    current_path = parent
                else:
                    current_path = norm_reports_root
            # Do not test the parent directory for being a symlink (it's not a user-selected component)
            continue
        
        # Any other component: append to current path to form new absolute prefix
        current_path = os.path.join(current_path, component)
        current_path = os.path.normpath(current_path)
        
        # Test whether that prefix exists and is a symbolic link using direct link predicate
        # Use os.lstat which does not follow symlinks, then check S_ISLNK
        try:
            stat_info = os.lstat(current_path)
            if os.path.islink(current_path):
                raise ValueError("Symbolic link detected in user-selected path component")
        except FileNotFoundError:
            # If the path doesn't exist, we can't test it for being a symlink
            # Continue to next component - but for the final component, this is expected
            # We only test symlinks on existing path components
            pass
    
    # 5) Open the normalized candidate path in text mode with UTF-8 encoding.
    # 6) If opening raises FileNotFoundError, propagate unmodified.
    # 7) Read, close, and return.
    with open(candidate, 'r', encoding='utf-8') as f:
        contents = f.read()
    
    return contents
