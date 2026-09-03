import os


def read_report(filename: str, reports_root: str) -> str:
    # 1) Join filename to reports_root and resolve to an absolute path
    reports_root = os.path.abspath(os.path.realpath(reports_root))
    requested_path = os.path.join(reports_root, filename)
    resolved_path = os.path.abspath(os.path.realpath(requested_path))

    # 2) Validate the resolved path remains strictly inside reports_root
    if not (
        resolved_path == reports_root
        or resolved_path.startswith(reports_root + os.sep)
    ):
        raise ValueError("Path escapes approved root directory")

    # 3) Check each user-selected path component for symlink status and reject if present
    # Split filename into components and walk from reports_root
    if filename:
        current_path = reports_root
        parts = filename.replace("\\", "/").split("/")
        for part in parts:
            if part == "" or part == ".":
                continue
            if part == "..":
                # Let the path resolution handle this; we check containment above
                # But we need to check symlink at each step
                next_path = os.path.normpath(os.path.join(current_path, part))
                # Check if the path component itself involves a symlink
                # Actually, we need to check if any path we'd traverse is a symlink
                # Walk carefully: check the target of each step
                pass
            
            next_path = os.path.join(current_path, part)
            # Check if this exact path is a symlink
            if os.path.islink(next_path):
                raise ValueError("Symbolic link encountered in path")
            # Also need to check intermediate symlinks in the path
            # os.path.realpath already resolved, but we need to reject if any symlink was used
            current_path = os.path.normpath(next_path) if os.path.exists(next_path) else next_path

    # Alternative: check that os.path.realpath of each prefix doesn't deviate due to symlinks
    # Actually, simpler: verify that walking the path manually, no component is a symlink
    current_path = reports_root
    parts = filename.replace("\\", "/").split("/")
    for part in parts:
        if part == "" or part == ".":
            continue
        next_path = os.path.join(current_path, part)
        if os.path.islink(next_path):
            raise ValueError("Symbolic link encountered in path")
        current_path = next_path

    # 4) Verify the target exists as an ordinary file
    if not os.path.exists(resolved_path):
        raise FileNotFoundError(f"File not found: {resolved_path}")
    if not os.path.isfile(resolved_path):
        raise ValueError("Target is not an ordinary file")

    # 5) Open in UTF-8 text mode and read contents
    with open(resolved_path, "r", encoding="utf-8") as f:
        return f.read()
