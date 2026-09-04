import os


def read_report(filename: str, reports_root: str) -> str:
    # 1) Resolve reports_root to an absolute path and normalize it lexically
    abs_reports_root = os.path.abspath(reports_root)
    norm_reports_root = os.path.normpath(abs_reports_root)

    # 2) Derive the normalized candidate absolute path
    joined_path = os.path.join(norm_reports_root, filename)
    norm_candidate = os.path.normpath(joined_path)

    # 3) Traversal validation
    # Ensure candidate is a strict descendant of reports_root
    if norm_candidate == norm_reports_root:
        raise ValueError("Path equals reports_root, not a strict descendant")
    # Use os.path.commonpath for reliable comparison
    try:
        common = os.path.commonpath([norm_candidate, norm_reports_root])
    except ValueError:
        # On Windows, different drives would raise ValueError
        raise ValueError("Path escapes reports_root")
    if common != norm_reports_root:
        raise ValueError("Path escapes reports_root")

    # 4) Symbolic-link validation by walking raw components
    logical_current = norm_reports_root
    # Split on platform path separator
    components = filename.split(os.sep)
    for component in components:
        # Ignore empty components and '.'
        if component == '' or component == '.':
            continue
        if component == '..':
            # Step up toward reports_root but never above it
            parent = os.path.dirname(logical_current)
            # Ensure we don't go above reports_root
            try:
                common_with_root = os.path.commonpath([parent, norm_reports_root])
            except ValueError:
                raise ValueError("Path escapes reports_root")
            if common_with_root != norm_reports_root:
                logical_current = norm_reports_root
            else:
                logical_current = parent
            # Do not test parent directory for being a symlink (not user-selected)
            continue
        # Any other component: append to logical current path
        new_prefix = os.path.join(logical_current, component)
        # Test whether that prefix exists and is a symbolic link
        # Use direct link predicate that does not traverse the link
        if os.path.islink(new_prefix):
            raise ValueError("Symbolic link detected in user-selected path component")
        logical_current = new_prefix

    # 5) Open the normalized candidate path in text mode with UTF-8 encoding
    # 6) If FileNotFoundError, propagate unmodified
    # 7) Read, close, and return
    with open(norm_candidate, 'r', encoding='utf-8') as f:
        return f.read()
