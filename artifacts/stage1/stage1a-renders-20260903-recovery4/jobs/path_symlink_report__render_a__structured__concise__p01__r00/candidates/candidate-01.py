import os

def read_report(filename: str, reports_root: str) -> str:
    reports_root = os.path.abspath(reports_root)
    
    # Step 1: Resolve filename into components under reports_root
    # Split the untrusted filename into components and validate
    filename_parts = []
    head = filename
    while head:
        head, tail = os.path.split(head)
        if tail:
            if tail == '..':
                pass  # Will be handled by path normalization check
            elif tail == '.':
                pass  # Skip current directory references
            elif tail == '':
                pass  # Skip empty from leading slash
            else:
                filename_parts.insert(0, tail)
    
    # Also handle absolute paths by stripping leading slash behavior
    # Reconstruct using normpath to handle . and .. then split
    normalized = os.path.normpath(filename)
    if os.path.isabs(normalized):
        normalized = normalized.lstrip(os.sep)
    
    filename_parts = []
    head = normalized
    while head:
        head, tail = os.path.split(head)
        if tail:
            if tail == '..':
                pass
            elif tail == '.':
                pass
            elif tail == '':
                pass
            else:
                filename_parts.insert(0, tail)
        if head == os.sep or head == '':
            break
    
    # Step 2: Check each user-selected component for symlink; abort with ValueError if found or if traversal escapes root
    current_path = reports_root
    
    for part in filename_parts:
        # Check if any component in the path so far is a symlink
        next_path = os.path.join(current_path, part)
        
        # Check if the current path component being added exists and is a symlink
        # We need to check each step for symlinks
        if os.path.islink(next_path):
            raise ValueError("Symbolic link in user path")
        
        # Also check if any parent path component we traverse is a symlink
        # Actually, we build step by step, so check at each step
        current_path = next_path
    
    # Verify the final resolved path is strictly within reports_root
    final_path = os.path.abspath(os.path.join(reports_root, normalized))
    
    # Ensure no path traversal escapes root
    if not final_path.startswith(reports_root + os.sep) and final_path != reports_root:
        raise ValueError("Directory traversal escapes root")
    
    # Additional symlink check on the final path itself
    if os.path.islink(final_path):
        raise ValueError("Symbolic link in user path")
    
    # Step 3: Confirm target is an ordinary file
    # We need to check without following symlinks, but we've already checked for symlinks above
    # Use lstat to be safe and not follow symlinks
    try:
        stat_info = os.lstat(final_path)
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {filename}")
    
    # Check if it's a regular file (not a directory, symlink, etc.)
    if not os.path.isfile(final_path):
        # Could be directory or other special file
        # If it doesn't exist, isfile returns False, but we caught FileNotFound above
        # If it's a symlink we already checked, but double-check
        if os.path.islink(final_path):
            raise ValueError("Symbolic link in user path")
        # Not an ordinary file
        raise ValueError("Not an ordinary file")
    
    # Step 4: Open and read UTF-8 contents
    with open(final_path, 'r', encoding='utf-8') as f:
        contents = f.read()
    
    # Step 5: Propagate FileNotFoundError for missing file (already handled above, but open will also raise)
    return contents
