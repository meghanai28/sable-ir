import os

def read_report(filename: str, reports_root: str) -> str:
    root = os.path.realpath(reports_root)
    if os.path.isabs(filename):
        raise ValueError("Absolute filename not allowed")
    requested = os.path.join(root, filename)
    try:
        resolved = os.path.realpath(requested)
    except OSError:
        raise ValueError("Failed to resolve path")
    try:
        common = os.path.commonpath([root, resolved])
    except ValueError:
        raise ValueError("Resolved path is outside approved root")
    if common != root:
        raise ValueError("Resolved path is outside approved root")
    if os.path.exists(resolved) and not os.path.isfile(resolved):
        raise ValueError("Not an ordinary file")
    with open(resolved, "r", encoding="utf-8") as f:
        return f.read()
