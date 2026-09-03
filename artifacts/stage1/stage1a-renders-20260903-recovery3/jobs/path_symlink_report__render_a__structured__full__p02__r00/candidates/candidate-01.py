import os


def read_report(filename: str, reports_root: str) -> str:
    # Step 1: Compute the absolute, normalized reports_root
    abs_root = os.path.abspath(os.path.normpath(reports_root))
    
    # Step 2: Verify filename is relative and does not start with a separator
    if os.path.isabs(filename):
        raise ValueError("filename must be relative")
    if filename.startswith(os.sep) or (os.altsep and filename.startswith(os.altsep)):
        raise ValueError("filename must not start with a path separator")
    
    # Step 3: Split filename into left-to-right components
    # Normalize separators first to handle mixed separators
    normalized_input = filename.replace(os.altsep, os.sep) if os.altsep else filename
    parts = [p for p in normalized_input.split(os.sep) if p]
    
    # Step 4: Initialize the accumulated path to reports_root
    accumulated = abs_root
    
    # Step 5: For each component, append and check for symlinks
    for part in parts:
        accumulated = os.path.join(accumulated, part)
        if os.path.islink(accumulated):
            raise ValueError("symbolic link encountered in path")
    
    # Step 6: Normalize the final accumulated path and confirm strict descendant
    final_path = os.path.normpath(accumulated)
    
    # Check if path is strictly beneath abs_root using commonpath
    try:
        common = os.path.commonpath([abs_root, final_path])
    except ValueError:
        # On Windows, paths on different drives raise ValueError
        raise ValueError("path escapes reports_root")
    
    if common != abs_root:
        raise ValueError("path escapes reports_root")
    
    if final_path == abs_root:
        raise ValueError("path must be strictly beneath reports_root")
    
    # Verify the normalized path is actually relative to root (handles case differences on Windows)
    try:
        rel = os.path.relpath(final_path, abs_root)
    except ValueError:
        raise ValueError("path escapes reports_root")
    
    if rel.startswith(os.pardir):
        raise ValueError("path escapes reports_root")
    
    # Step 7: Confirm the target is an ordinary file
    # Allow FileNotFoundError to propagate naturally for missing targets
    if os.path.exists(final_path) and not os.path.isfile(final_path):
        raise ValueError("target is not an ordinary file")
    
    # Step 8: Open, read, and return UTF-8 contents
    with open(final_path, 'r', encoding='utf-8') as f:
        return f.read()
