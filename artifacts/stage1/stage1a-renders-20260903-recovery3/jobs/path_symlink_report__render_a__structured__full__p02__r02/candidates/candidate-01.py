import os
import pathlib


def read_report(filename: str, reports_root: str) -> str:
    # Step 1: Compute the absolute, normalized reports_root
    abs_root = os.path.abspath(os.path.normpath(reports_root))
    
    # Step 2: Verify filename is relative and does not start with a separator
    if os.path.isabs(filename):
        raise ValueError("filename must be relative")
    if filename.startswith(os.sep) or (os.altsep is not None and filename.startswith(os.altsep)):
        raise ValueError("filename must not start with a path separator")
    
    # Step 3: Split filename into left-to-right components
    # Use pathlib to handle splitting correctly across platforms
    parts = pathlib.PurePath(filename).parts
    
    # Step 4: Initialize the accumulated path to reports_root
    accumulated = abs_root
    
    # Step 5: For each component in order, append and check for symlinks
    for part in parts:
        accumulated = os.path.join(accumulated, part)
        # Check if the accumulated path is a symbolic link (without following)
        if os.path.islink(accumulated):
            raise ValueError("symbolic link encountered in path")
    
    # Step 6: Normalize the final accumulated path and confirm strict descendant
    normalized_path = os.path.normpath(accumulated)
    
    # Use commonpath for robust comparison
    try:
        common = os.path.commonpath([abs_root, normalized_path])
    except ValueError:
        # On Windows, different drives raise ValueError
        raise ValueError("path escapes reports_root")
    
    if common != abs_root:
        raise ValueError("path escapes reports_root")
    
    # Strict descendant check: normalized_path must not equal abs_root
    if normalized_path == abs_root:
        raise ValueError("path must be strictly beneath reports_root")
    
    # Additional check: ensure normalized_path is truly a descendant
    # Using pathlib for robust relative-to check
    try:
        path_obj = pathlib.Path(normalized_path)
        root_obj = pathlib.Path(abs_root)
        if not path_obj.is_relative_to(root_obj) or path_obj == root_obj:
            raise ValueError("path must be strictly beneath reports_root")
    except AttributeError:
        # Python < 3.9 fallback
        try:
            rel_path = os.path.relpath(normalized_path, abs_root)
            if rel_path == '.' or rel_path.startswith('..'):
                raise ValueError("path must be strictly beneath reports_root")
        except ValueError:
            raise ValueError("path escapes reports_root")
    
    # Step 7: Confirm the target is an ordinary file
    # Permit FileNotFoundError for missing targets
    if os.path.exists(normalized_path):
        if not os.path.isfile(normalized_path):
            raise ValueError("target is not an ordinary file")
    # If it doesn't exist, we'll let the open call raise FileNotFoundError
    
    # Step 8: Open the validated path in text mode with UTF-8 encoding and read
    with open(normalized_path, 'r', encoding='utf-8') as f:
        return f.read()
