import os

def read_report(filename: str, reports_root: str) -> str:
    # Step 1: Resolve reports_root to an absolute path and normalize it lexically
    abs_reports_root = os.path.abspath(reports_root)
    
    # Step 2: Derive the normalized candidate absolute path
    candidate = os.path.normpath(os.path.join(abs_reports_root, filename))
    
    # Step 3: Traversal validation - confirm candidate is a strict descendant of reports_root
    # Add trailing separator to reports_root to ensure strict prefix matching
    prefix = abs_reports_root
    if not prefix.endswith(os.sep):
        prefix += os.sep
    
    if not candidate.startswith(prefix) and candidate != abs_reports_root:
        # On Windows, also check with alternative separator
        if os.name == 'nt':
            prefix_alt = abs_reports_root.replace(os.sep, '/')
            if not prefix_alt.endswith('/'):
                prefix_alt += '/'
            candidate_alt = candidate.replace(os.sep, '/')
            if not candidate_alt.startswith(prefix_alt) and candidate_alt != prefix_alt.rstrip('/'):
                raise ValueError("Path escapes the approved root directory")
        else:
            raise ValueError("Path escapes the approved root directory")
    elif candidate == abs_reports_root or candidate == abs_reports_root + os.sep.rstrip(os.sep):
        raise ValueError("Path must be a strict descendant of the approved root directory")
    
    # Step 4: Symbolic-link validation by walking raw components
    current_path = abs_reports_root
    components = filename.split(os.sep)
    
    for component in components:
        # Ignore empty components and '.'
        if component == '' or component == '.':
            continue
        
        if component == '..':
            # Step up toward reports_root but never above it
            parent = os.path.dirname(current_path)
            # Only step up if we would not go above reports_root
            if len(parent) >= len(abs_reports_root):
                # Additional check: ensure we don't go above by prefix check
                if parent == abs_reports_root or (parent + os.sep).startswith(abs_reports_root + os.sep) or parent.startswith(abs_reports_root + os.sep):
                    current_path = parent
                else:
                    current_path = abs_reports_root
            else:
                current_path = abs_reports_root
        else:
            # Form new absolute prefix
            new_path = os.path.join(current_path, component)
            # Test whether this prefix exists and is a symbolic link
            # Use direct link predicate that does not traverse the link
            if os.path.islink(new_path):
                raise ValueError("Symbolic link detected in user-selected path component")
            current_path = new_path
    
    # Step 5-7: Open, read, and return; propagate FileNotFoundError
    with open(candidate, 'r', encoding='utf-8') as f:
        return f.read()
