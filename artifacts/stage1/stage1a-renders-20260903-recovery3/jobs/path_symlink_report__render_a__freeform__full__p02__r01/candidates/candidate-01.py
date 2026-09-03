import os
import stat


def read_report(filename: str, reports_root: str) -> str:
    # Resolve reports_root to an absolute path to establish a stable trusted boundary
    abs_reports_root = os.path.abspath(reports_root)
    
    # Ensure reports_root ends with a separator for proper prefix checking
    # (os.path.join handles this, but we need strict prefix comparison later)
    
    # Form the candidate path by joining reports_root with the supplied filename
    candidate_path = os.path.join(abs_reports_root, filename)
    
    # Normalize the result textually to remove . entries, redundant separators, and .. sequences
    normalized_path = os.path.normpath(candidate_path)
    
    # Reject if the normalized path equals reports_root or steps outside it via directory traversal
    # The target must reside strictly beneath the approved root
    if normalized_path == abs_reports_root:
        raise ValueError("Path must be strictly beneath reports_root")
    
    # Use os.path.realpath on the reports_root to handle any symlinks in the root itself
    # But we compare using the normalized path to ensure strict containment
    # We need to ensure normalized_path is still within abs_reports_root after normalization
    
    # Check that normalized_path is strictly beneath abs_reports_root
    # Use os.path.commonpath for reliable comparison, or prefix check with separator
    try:
        # Ensure the normalized path is actually under reports_root
        relative = os.path.relpath(normalized_path, abs_reports_root)
        if relative == '.' or relative.startswith('..'):
            raise ValueError("Path traversal outside reports_root detected")
    except ValueError:
        raise ValueError("Path traversal outside reports_root detected")
    
    # Additional check: ensure normalized_path starts with abs_reports_root + separator
    # or is exactly abs_reports_root (already checked above)
    # This handles edge cases with path prefix matching
    if not normalized_path.startswith(abs_reports_root + os.sep) and normalized_path != abs_reports_root:
        # Handle the case where abs_reports_root ends with os.sep (root directory on Windows, etc.)
        if not (abs_reports_root.endswith(os.sep) and normalized_path.startswith(abs_reports_root)):
            raise ValueError("Path traversal outside reports_root detected")
    
    # Enforce the symbolic-link prohibition by inspecting every filesystem node
    # that corresponds to a user-selected path component derived from filename.
    # Walk the normalized candidate path from the first component after reports_root through the final filename.
    
    # Get the path components after reports_root
    # We walk from the first component after reports_root through the final filename
    
    # Build up the path component by component, starting from reports_root
    current_path = abs_reports_root
    
    # Get the relative path from reports_root to normalized_path
    rel_path = os.path.relpath(normalized_path, abs_reports_root)
    
    # Split into components and walk
    if rel_path == '.':
        raise ValueError("Path must be strictly beneath reports_root")
    
    # Handle platform-specific path separators
    path_components = rel_path.split(os.sep)
    
    for component in path_components:
        if component == '' or component == '.':
            continue
        current_path = os.path.join(current_path, component)
        
        # Perform a non-following link check using semantics equivalent to lstat or islink
        # that does not traverse symbolic links.
        try:
            # Use os.lstat to not follow symlinks
            file_stat = os.lstat(current_path)
            # Check if this is a symbolic link
            if stat.S_ISLNK(file_stat.st_mode):
                raise ValueError("Symbolic link detected in user-selected path")
        except OSError:
            # If the path doesn't exist yet, that's okay for intermediate directories
            # But we need to check if the final component exists or if intermediate dirs exist
            # If it's not the final component and it doesn't exist, that's an error for traversal
            # However, we allow FileNotFoundError to propagate only for the final open operation
            # For symlink checking, if a component doesn't exist, we can't check if it's a symlink
            # So we stop checking further components if this one doesn't exist
            # But we need to be careful: if this is an intermediate directory that doesn't exist,
            # the final open will fail with FileNotFoundError, which is correct
            
            # Check if this is the final component
            if current_path == normalized_path:
                # Final component doesn't exist, which is fine - let FileNotFoundError propagate on open
                pass
            # For intermediate components that don't exist, we can't check them for symlinks
            # The open will fail later with FileNotFoundError if the path is invalid
            break
    
    # After confirming that the target path is strictly within reports_root and that
    # no user-selected path component is a symbolic link, attempt to open the target as a UTF-8 text file.
    
    # Open and read the file, allowing FileNotFoundError to propagate naturally
    with open(normalized_path, 'r', encoding='utf-8') as f:
        contents = f.read()
    
    return contents
