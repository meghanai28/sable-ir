import os

def read_report(filename: str, reports_root: str) -> str:
    # Resolve the reports_root to an absolute path to ensure consistent handling
    resolved_root = os.path.abspath(reports_root)
    
    # Normalize the requested filename to prevent path traversal
    # We resolve it relative to the root, then normalize it
    requested_path = os.path.normpath(os.path.join(reports_root, filename))
    
    # Ensure the resolved path is within the reports_root
    # Use os.path.commonpath to verify the paths share the same prefix
    common = os.path.commonpath([resolved_root, requested_path])
    if common != resolved_root:
        raise ValueError("Request escapes the reports_root directory")
    
    # Walk each user-selected path component and check for symbolic links
    # We split the path by separators and check each component
    parts = requested_path.split(os.sep)
    current_path = resolved_root
    
    for part in parts:
        if part == '' or part == '.':
            continue
        if part == '..':
            # This should have been caught by normpath, but we check anyway
            pass
        
        # Check if the current path exists and is a symlink before moving down
        if os.path.islink(current_path):
            raise ValueError("Symbolic link detected in path")
        
        next_path = os.path.join(current_path, part)
        if not os.path.exists(next_path):
            # If it doesn't exist yet, we can't check for symlinks in the directory
            # But we can check if it's a symlink if it exists
            pass
        
        # Actually, we need to check the directory we are about to enter
        if os.path.isdir(current_path):
            if os.path.islink(current_path):
                raise ValueError("Symbolic link detected in path")
        
        current_path = next_path
    
    # Final check on the target file
    if os.path.islink(requested_path):
        raise ValueError("Symbolic link detected in target file")
    
    # Check if the file exists and is a regular file
    if not os.path.isfile(requested_path):
        raise FileNotFoundError(f"The file {filename} does not exist")
    
    # Read and return the UTF-8 text
    with open(requested_path, 'r', encoding='utf-8') as f:
        return f.read()
