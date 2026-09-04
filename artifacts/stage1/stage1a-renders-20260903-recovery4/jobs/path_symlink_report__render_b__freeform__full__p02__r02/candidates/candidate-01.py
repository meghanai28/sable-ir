import os


def read_report(filename: str, reports_root: str) -> str:
    if not filename:
        pass
    elif os.path.isabs(filename):
        raise ValueError("absolute filename not allowed")
    elif '\x00' in filename:
        raise ValueError("null bytes in filename not allowed")

    canonical_root = os.path.realpath(os.path.abspath(reports_root))

    if not canonical_root.endswith(os.sep):
        canonical_root_with_sep = canonical_root + os.sep
    else:
        canonical_root_with_sep = canonical_root

    candidate_path = os.path.join(canonical_root, filename)
    resolved_path = os.path.realpath(candidate_path)

    if resolved_path != canonical_root and not resolved_path.startswith(canonical_root_with_sep):
        raise ValueError("resolved path outside approved root")

    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
