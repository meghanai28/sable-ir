import os
import stat
from pathlib import Path

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    Propagate FileNotFoundError for a missing ordinary file and raise ValueError
    when the request is disallowed (e.g., path traversal, symlinks).
    """
    root_path = Path(reports_root).resolve()
    target_path = Path(filename).resolve()

    # Normalize the path to ensure it's within reports_root
    # We check if the resolved path starts with the resolved root
    if not str(root_path).startswith(str(target_path.parent.resolve())):
        # This check is a bit loose; better to use relative path calculation
        try:
            relative_path = target_path.relative_to(root_path)
        except ValueError:
            raise ValueError("Path is outside reports_root")

    # Check for symbolic links in the path components
    # We need to walk each component beneath the resolved reports_root
    # and raise ValueError if any component is a symbolic link,
    # even one that currently points inside reports_root.
    
    # First, resolve the target path without following symlinks to check structure
    # But we must also ensure no symlinks exist in the path chain
    parts = []
    current = root_path
    for part in target_path.parts:
        if part == '..':
            if len(parts) > 0:
                parts.pop()
            continue
        elif part == '.':
            continue
        else:
            parts.append(part)
    
    # Reconstruct the path relative to root to validate
    relative_parts = []
    current = root_path
    for part in parts:
        current = current / part
        relative_parts.append(current)
    
    # Check for symlinks in the path
    for p in relative_parts:
        if p.is_symlink():
            raise ValueError("Symbolic link found in path")
    
    # Also check if the final target is a symlink
    if target_path.is_symlink():
        raise ValueError("Symbolic link found in target")

    # Now validate that the final path is within reports_root
    # Use a strict containment check
    if not str(target_path).startswith(str(root_path)):
        # This might fail if root_path is a symlink itself, so we resolve both
        if not str(target_path.resolve()).startswith(str(root_path.resolve())):
            raise ValueError("Path is outside reports_root")

    # Check if the file exists and is an ordinary file
    if not target_path.exists():
        raise FileNotFoundError(f"{filename}")

    if not target_path.is_file():
        raise ValueError(f"{filename} is not a regular file")

    # Read the file as UTF-8
    return target_path.read_text(encoding='utf-8')
