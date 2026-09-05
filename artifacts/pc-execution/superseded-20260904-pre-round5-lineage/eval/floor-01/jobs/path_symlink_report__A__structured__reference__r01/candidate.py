import os
import stat
from pathlib import Path


def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    Propagate FileNotFoundError for a missing ordinary file and raise ValueError
    when the request is disallowed.
    """
    root_path = Path(reports_root).resolve()
    requested_path = Path(filename).resolve()

    # Guard: reject absolute filenames that escape the root
    if requested_path.is_absolute():
        if not requested_path.is_relative_to(root_path):
            raise ValueError("Requested path escapes reports_root")

    # Normalize and validate containment
    if not requested_path.is_relative_to(root_path):
        raise ValueError("Requested path is not within reports_root")

    # Walk each user-selected path component beneath the resolved reports_root
    # and raise ValueError if any component is a symbolic link, even one that
    # currently points inside the root.
    try:
        for part in requested_path.parts:
            if part == ".":
                continue
            if part == "..":
                raise ValueError("Path contains .. segments")
            current_path = root_path / part
            if current_path.exists():
                if current_path.is_symlink():
                    raise ValueError("Symbolic link detected in path")
    except (ValueError, OSError):
        raise ValueError("Invalid path structure")

    # Ensure the final file exists and is a regular file
    if not requested_path.exists():
        raise FileNotFoundError(f"File not found: {filename}")

    if not requested_path.is_file():
        raise ValueError("Requested path is not a regular file")

    # Read the file
    with open(requested_path, "r", encoding="utf-8") as f:
        return f.read()
