import os

def read_report(filename: str, reports_root: str) -> str:
    root = os.path.abspath(reports_root)

    if os.path.isabs(filename):
        raise ValueError("Request disallowed")

    if "\x00" in filename:
        raise ValueError("Request disallowed")

    normalized = filename.replace(os.altsep, os.sep) if os.altsep else filename
    parts = normalized.split(os.sep)

    if any(part == ".." for part in parts):
        raise ValueError("Request disallowed")

    current = root
    for part in parts:
        if part == "" or part == ".":
            continue
        next_path = os.path.join(current, part)
        if os.path.islink(next_path):
            raise ValueError("Request disallowed")
        current = next_path

    target = os.path.normpath(current)

    if target == root:
        raise ValueError("Request disallowed")

    try:
        if os.path.commonpath([target, root]) != root:
            raise ValueError("Request disallowed")
    except ValueError:
        raise ValueError("Request disallowed")

    with open(target, "r", encoding="utf-8") as f:
        return f.read()
