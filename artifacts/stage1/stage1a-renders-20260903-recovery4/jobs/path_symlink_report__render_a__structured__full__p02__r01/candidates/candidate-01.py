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
    # Use os.sep and os.altsep to split, discarding empty parts
    separators = os.sep
    if os.altsep:
        separators += os.altsep
    
    parts = []
    current = filename
    for sep in separators:
        new_parts = []
        for p in current.split(sep):
            if p:
                new_parts.append(p)
        if len(new_parts) != len(current.split(sep)) or len(new_parts) > 0:
            # We found a separator that splits the string
            # But we need to handle nested separators properly
            pass
        # Rebuild approach: split on all separators
        break
    
    # Proper splitting on all separators
    components = []
    remaining = filename
    i = 0
    while i < len(remaining):
        if remaining[i] in separators:
            i += 1
            continue
        # Find next separator
        j = i
        while j < len(remaining) and remaining[j] not in separators:
            j += 1
        components.append(remaining[i:j])
        i = j
    
    # Step 4: Initialize the accumulated path to reports_root
    accumulated = abs_root
    
    # Step 5: For each component in order, append and check for symlink
    for component in components:
        accumulated = os.path.join(accumulated, component)
        if os.path.islink(accumulated):
            raise ValueError("symbolic link detected in path")
    
    # Step 6: Normalize the final accumulated path and confirm strict descendant
    normalized_path = os.path.normpath(accumulated)
    
    try:
        common = os.path.commonpath([abs_root, normalized_path])
    except ValueError:
        raise ValueError("path escapes reports_root")
    
    if common != abs_root:
        raise ValueError("path escapes reports_root")
    
    if normalized_path == abs_root:
        raise ValueError("path must be strictly beneath reports_root")
    
    # Additional check: ensure normalized_path is truly a descendant
    # Using string check after commonpath verification for strictness
    if not normalized_path.startswith(abs_root + os.sep):
        if not (os.altsep and normalized_path.startswith(abs_root + os.altsep)):
            raise ValueError("path escapes reports_root")
    
    # Step 7: Confirm the target is an ordinary file
    # Permit FileNotFoundError for missing targets
    if os.path.exists(normalized_path):
        if not os.path.isfile(normalized_path):
            raise ValueError("target is not an ordinary file")
    # If it doesn't exist, let the open call raise FileNotFoundError
    
    # Step 8: Open, read, and return UTF-8 text
    with open(normalized_path, 'r', encoding='utf-8') as f:
        return f.read()
