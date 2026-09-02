from pathlib import Path


def read_report(filename: str, reports_root: str) -> str:
    root = Path(reports_root).resolve(strict=True)
    requested = Path(filename)
    if requested.is_absolute() or ".." in requested.parts:
        raise ValueError("report path is outside the allowed root")

    candidate = root
    for component in requested.parts:
        candidate = candidate / component
        if candidate.is_symlink():
            raise ValueError("symbolic links are not permitted")

    resolved = candidate.resolve(strict=True)
    if not resolved.is_relative_to(root):
        raise ValueError("report path is outside the allowed root")
    return resolved.read_text(encoding="utf-8")
