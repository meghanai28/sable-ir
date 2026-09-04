import os


def read_report(filename: str, reports_root: str) -> str:
    # Resolve reports_root to an absolute path for a stable trusted boundary
    abs_root = os.path.abspath(reports_root)
    
    # Form the candidate path by joining and normalizing
    candidate = os.path.normpath(os.path.join(abs_root, filename))
    
    # Reject if normalized path equals reports_root or steps outside it
    if candidate == abs_root:
        raise ValueError("Request disallowed: path equals reports_root")
    
    # Ensure the candidate is strictly beneath reports_root
    # Use os.path.commonpath for reliable containment check
    try:
        common = os.path.commonpath([candidate, abs_root])
    except ValueError:
        # On Windows, paths on different drives raise ValueError
        raise ValueError("Request disallowed: path outside reports_root")
    
    if common != abs_root:
        raise ValueError("Request disallowed: path outside reports_root")
    
    # Enforce symbolic-link prohibition on user-selected path components
    # Walk from first component after reports_root through final filename
    # Get the relative path from abs_root to candidate
    rel_path = os.path.relpath(candidate, abs_root)
    
    # Build up each prefix and check for symlinks
    current = abs_root
    # Handle the case where rel_path might be '.' or empty (already caught above)
    if rel_path == '.':
        raise ValueError("Request disallowed: path equals reports_root")
    
    # Split the relative path into components
    components = rel_path.split(os.sep)
    
    for component in components:
        current = os.path.join(current, component)
        # Perform non-following link check
        if os.path.islink(current):
            raise ValueError("Request disallowed: symbolic link detected")
    
    # After confirming no symlinks in user-selected components, open the file
    # Allow FileNotFoundError to propagate naturally if file doesn't exist
    with open(current, 'r', encoding='utf-8') as f:
        return f.read()
