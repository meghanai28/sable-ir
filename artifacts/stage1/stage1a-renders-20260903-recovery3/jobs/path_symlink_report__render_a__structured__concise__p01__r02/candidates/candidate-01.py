import os

def read_report(filename: str, reports_root: str) -> str:
    # Step 1: Resolve filename into components under reports_root
    # Normalize reports_root to absolute path
    reports_root = os.path.abspath(reports_root)
    
    # Split filename into components and reject absolute paths or empty paths
    if not filename or filename.startswith('/'):
        raise ValueError("Invalid filename")
    
    # Split into components
    components = filename.split('/')
    
    # Filter out empty components (from consecutive slashes or trailing slash)
    components = [c for c in components if c]
    
    if not components:
        raise ValueError("Invalid filename")
    
    # Step 2: Check each user-selected component for symlink and build path incrementally
    current_path = reports_root
    
    for component in components:
        # Reject parent directory references
        if component == '..':
            raise ValueError("Directory traversal not allowed")
        
        # Reject current directory references for clarity (though harmless)
        if component == '.':
            raise ValueError("Invalid path component")
        
        # Build next path incrementally
        next_path = os.path.join(current_path, component)
        
        # Check if the current path component (as built) is a symlink
        # We check at each step to catch symlinks in intermediate directories too
        if os.path.islink(next_path):
            raise ValueError("Symbolic link not allowed")
        
        current_path = next_path
    
    # Final resolved path
    resolved_path = current_path
    
    # Verify the resolved path is strictly within reports_root
    real_resolved = os.path.realpath(resolved_path)
    real_root = os.path.realpath(reports_root)
    
    if not real_resolved.startswith(real_root + os.sep) and real_resolved != real_root:
        raise ValueError("Path escapes approved root")
    
    # Step 3: Confirm target is an ordinary file
    # Use lstat to not follow symlinks (though we already checked)
    try:
        stat_info = os.lstat(resolved_path)
    except FileNotFoundError:
        raise
    
    # Check it's a regular file, not a directory or other special file
    if not os.path.isfile(resolved_path):
        raise ValueError("Not an ordinary file")
    
    # Additional check: ensure it's not a symlink (race condition protection)
    if os.path.islink(resolved_path):
        raise ValueError("Symbolic link not allowed")
    
    # Step 4: Open and read UTF-8 contents
    with open(resolved_path, 'r', encoding='utf-8') as f:
        contents = f.read()
    
    # Step 5: Return contents (FileNotFoundError already propagated above)
    return contents
