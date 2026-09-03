import os


def read_report(filename: str, reports_root: str) -> str:
    canonical_root = os.path.realpath(reports_root)
    candidate = os.path.join(canonical_root, filename)
    resolved_target = os.path.realpath(candidate)
    if os.path.commonpath([canonical_root, resolved_target]) != canonical_root:
        raise ValueError("Request disallowed: path resolves outside approved root")
    if resolved_target == canonical_root:
        raise ValueError("Request disallowed: path resolves to root directory")
    with open(resolved_target, encoding="utf-8") as f:
        return f.read()
