import os


def read_report(filename: str, reports_root: str) -> str:
    # Step 1: Resolve reports_root to an absolute path and normalize it lexically.
    abs_reports_root = os.path.abspath(reports_root)
    norm_reports_root = os.path.normpath(abs_reports_root)

    # Step 2: Derive the normalized candidate absolute path.
    joined_path = os.path.join(norm_reports_root, filename)
    candidate = os.path.normpath(joined_path)

    # Step 3: Traversal validation.
    # Candidate must be a strict descendant of reports_root.
    # Use os.path.join to ensure reports_root ends with separator for prefix check.
    prefix_check = os.path.join(norm_reports_root, '')
    if not candidate.startswith(prefix_check):
        raise ValueError("Path escapes the approved root directory")
    if candidate == norm_reports_root:
        raise ValueError("Path equals the approved root directory")

    # Step 4: Symbolic-link validation.
    # Walk raw components of filename without following symlinks.
    logical_current = norm_reports_root
    components = filename.split(os.sep)

    for component in components:
        if component == '' or component == '.':
            continue
        if component == '..':
            # Step up toward reports_root but never above it.
            parent = os.path.dirname(logical_current)
            if len(parent) >= len(norm_reports_root):
                logical_current = parent
            else:
                logical_current = norm_reports_root
            continue
        # Any other component: form new absolute prefix and test for symlink.
        new_prefix = os.path.join(logical_current, component)
        # Use direct link predicate that does not traverse the link.
        if os.path.islink(new_prefix):
            raise ValueError("Symbolic link detected in path")
        logical_current = new_prefix

    # Step 5, 6, 7: Open, read, and return.
    with open(candidate, mode='r', encoding='utf-8') as f:
        return f.read()
