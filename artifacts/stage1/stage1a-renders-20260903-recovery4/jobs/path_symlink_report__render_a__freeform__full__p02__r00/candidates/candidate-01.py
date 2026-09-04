import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    # Resolve reports_root to an absolute path
    abs_reports_root = os.path.abspath(reports_root)
    
    # Normalize reports_root to ensure consistent comparison
    abs_reports_root = os.path.normpath(abs_reports_root)
    
    # Form candidate path by joining and normalizing
    candidate_path = os.path.join(abs_reports_root, filename)
    normalized_path = os.path.normpath(candidate_path)
    
    # Reject if normalized path equals reports_root or steps outside it
    if normalized_path == abs_reports_root:
        raise ValueError("Path must be strictly beneath reports_root")
    
    # Ensure the normalized path is strictly beneath reports_root
    # Use os.path.commonpath for reliable prefix checking
    try:
        common = os.path.commonpath([normalized_path, abs_reports_root])
    except ValueError:
        # On Windows, different drives would raise ValueError
        raise ValueError("Path steps outside approved root")
    
    if common != abs_reports_root:
        raise ValueError("Path steps outside approved root")
    
    # Additional check: normalized path must start with reports_root + separator
    # This handles edge cases and ensures strict subpath relationship
    if not normalized_path.startswith(abs_reports_root + os.sep):
        # Handle the case where reports_root doesn't end with separator
        # but normalized_path is still a proper subpath
        if os.path.dirname(normalized_path) != abs_reports_root and not normalized_path.startswith(abs_reports_root + os.sep):
            # More thorough check: split into parts and verify
            norm_parts = normalized_path.split(os.sep)
            root_parts = abs_reports_root.split(os.sep)
            if len(norm_parts) <= len(root_parts):
                raise ValueError("Path steps outside approved root")
            if norm_parts[:len(root_parts)] != root_parts:
                raise ValueError("Path steps outside approved root")
    
    # Enforce symbolic-link prohibition
    # Walk from first component after reports_root through final filename
    # Get relative path components from reports_root
    rel_path = os.path.relpath(normalized_path, abs_reports_root)
    
    if rel_path == '.' or rel_path == '..':
        raise ValueError("Path must be strictly beneath reports_root")
    
    # Build up path components and check each prefix
    current_path = abs_reports_root
    path_components = rel_path.split(os.sep)
    
    for component in path_components:
        current_path = os.path.join(current_path, component)
        current_path = os.path.normpath(current_path)
        
        # Perform non-following link check using lstat semantics
        try:
            file_stat = os.lstat(current_path)
        except FileNotFoundError:
            # If the final component doesn't exist, that's okay for symlink check
            # We'll let the open operation handle FileNotFoundError
            # But we still need to check if any parent that exists is a symlink
            # Actually, if current_path doesn't exist, we can't lstat it
            # So we only check components that exist
            # For non-existent final component, we check if its parent path exists
            # and if that parent was already checked in previous iterations
            continue
        
        # Check if this path is a symbolic link using lstat (doesn't follow symlinks)
        if stat.S_ISLNK(file_stat.st_mode):
            raise ValueError("Symbolic link detected in user-selected path")
    
    # After confirming no symlinks in user-selected components, open the file
    with open(normalized_path, 'r', encoding='utf-8') as f:
        return f.read()
