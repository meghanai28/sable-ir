import os
import pathlib


def read_report(filename: str, reports_root: str) -> str:
    # Step 1: Compute the absolute, normalized reports_root
    root_path = os.path.abspath(os.path.normpath(reports_root))
    
    # Step 2: Verify filename is relative and does not start with a separator
    if os.path.isabs(filename):
        raise ValueError("filename must be relative")
    
    # Check if filename starts with a path separator
    if filename.startswith(os.sep) or filename.startswith('/'):
        raise ValueError("filename must not start with a path separator")
    
    # Also check for backslash on Windows or mixed separators
    if os.altsep and filename.startswith(os.altsep):
        raise ValueError("filename must not start with a path separator")
    
    # Step 3: Split filename into left-to-right components
    # Normalize separators first to handle mixed separators
    normalized_filename = filename.replace('/', os.sep)
    if os.altsep:
        normalized_filename = normalized_filename.replace(os.altsep, os.sep)
    
    # Split on separator and discard empty parts
    components = [comp for comp in normalized_filename.split(os.sep) if comp]
    
    # If no components remain after filtering, raise ValueError
    if not components:
        raise ValueError("filename must contain at least one path component")
    
    # Step 4: Initialize the accumulated path to reports_root
    accumulated_path = root_path
    
    # Step 5: For each component, append and check for symlinks
    for component in components:
        accumulated_path = os.path.join(accumulated_path, component)
        
        # Check if the accumulated path is a symbolic link (without following)
        if os.path.islink(accumulated_path):
            raise ValueError("symbolic link detected in path")
    
    # Step 6: Normalize the final accumulated path
    final_path = os.path.normpath(accumulated_path)
    
    # Verify strict descendant of reports_root using robust comparison
    try:
        common = os.path.commonpath([root_path, final_path])
    except ValueError:
        # On Windows, this can happen with different drives
        raise ValueError("path escapes reports_root")
    
    if common != root_path:
        raise ValueError("path escapes reports_root")
    
    # Also check that final_path is not equal to root_path (strict descendant)
    if os.path.samefile(final_path, root_path) if os.path.exists(final_path) else final_path == root_path:
        raise ValueError("path must be strictly beneath reports_root")
    
    # Additional check: final_path should not equal root_path
    if os.path.normpath(final_path) == os.path.normpath(root_path):
        raise ValueError("path must be strictly beneath reports_root")
    
    # Use pathlib for is_relative_to check as additional robust validation
    final_path_obj = pathlib.Path(final_path)
    root_path_obj = pathlib.Path(root_path)
    
    try:
        # Python 3.9+ has is_relative_to
        if hasattr(final_path_obj, 'is_relative_to'):
            if not final_path_obj.is_relative_to(root_path_obj):
                raise ValueError("path escapes reports_root")
            # Ensure strict relative (not equal)
            if final_path_obj == root_path_obj:
                raise ValueError("path must be strictly beneath reports_root")
        else:
            # Fallback for older Python: manual check
            try:
                relative = final_path_obj.relative_to(root_path_obj)
                if str(relative) == '.':
                    raise ValueError("path must be strictly beneath reports_root")
            except ValueError:
                raise ValueError("path escapes reports_root")
    except ValueError as e:
        if "path must be strictly beneath reports_root" in str(e) or "path escapes reports_root" in str(e):
            raise
        raise ValueError("path escapes reports_root")
    
    # Step 7: Confirm the target is an ordinary file
    # If path doesn't exist, allow FileNotFoundError from open
    if os.path.exists(final_path):
        if not os.path.isfile(final_path):
            raise ValueError("target is not an ordinary file")
    # If not exists, we proceed to open and let FileNotFoundError propagate
    
    # Step 8: Open and read the file
    with open(final_path, 'r', encoding='utf-8') as f:
        return f.read()
