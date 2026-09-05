import os

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    Propagates FileNotFoundError for a missing ordinary file and raises ValueError
    when the request is disallowed.
    """
    # Resolve the base directory
    resolved_root = os.path.realpath(reports_root)
    
    # Validate the filename: reject absolute paths
    if os.path.isabs(filename):
        raise ValueError("Absolute filenames are not allowed")
    
    # Construct the full path without resolving symlinks yet for normalization
    # We need to ensure the final resolved path stays within the root
    # First, construct the path as if it were relative to the root, but handle .. segments
    # by normalizing it relative to the root first.
    
    # Create a temporary path to normalize relative to root
    # We split the filename into components to handle .. and . safely
    parts = filename.split(os.sep) if os.sep in filename else filename.split('/')
    
    # Reconstruct path relative to root to normalize it properly
    # This handles .. segments correctly
    rel_path_parts = []
    for part in parts:
        if part == '' or part == '.':
            continue
        elif part == '..':
            if not rel_path_parts:
                raise ValueError("Path traversal attempt detected")
            rel_path_parts.pop()
        else:
            rel_path_parts.append(part)
    
    # Construct the full candidate path
    candidate_path = os.path.join(resolved_root, *rel_path_parts)
    
    # Resolve the candidate path to check for escape attempts
    # os.path.realpath will resolve symlinks, but we need to check if the resolved path
    # is within the root before we actually open it.
    # However, the plan says: "normalize the requested path and raise ValueError if it escapes"
    # and "walk each user-selected path component... raise ValueError if any component is a symbolic link"
    
    # Let's resolve the candidate path to see if it escapes the root
    resolved_candidate = os.path.realpath(candidate_path)
    
    # Check if the resolved candidate is outside the resolved root
    # We need to handle the case where the root itself might be a symlink
    # by comparing the resolved_root directory, not the root itself
    root_dir = os.path.dirname(resolved_root)
    
    if not resolved_candidate.startswith(root_dir + os.sep) and resolved_candidate != root_dir:
        raise ValueError("Path escapes the reports_root directory")
    
    # Now walk each user-selected path component and check for symbolic links
    # We need to check each component of the path as we traverse
    current_path = candidate_path
    
    # Split the path into components (excluding the root)
    components = [p for p in rel_path_parts if p]
    
    for i, component in enumerate(components):
        # Check if the current path (up to this component) is a symlink
        # We check the path before resolving the current component to avoid following symlinks in the chain
        # Actually, the plan says "even one that currently points inside the root"
        # So we should check if any component in the path is a symlink
        
        # Build the path up to this component
        path_up_to = os.path.join(resolved_root, *components[:i+1])
        
        # Check if this path is a symbolic link
        if os.path.islink(path_up_to):
            raise ValueError("Symbolic link detected in path")
        
        # Also check if the parent directory of this component is a symlink
        # This covers cases like: root/.. -> symlink -> target
        parent_dir = os.path.dirname(path_up_to)
        if parent_dir != resolved_root and os.path.islink(parent_dir):
            raise ValueError("Symbolic link detected in path components")
    
    # Now check if the final file exists and is an ordinary file
    if not os.path.isfile(candidate_path):
        raise FileNotFoundError(f"File not found: {filename}")
    
    # Read the file content
    with open(candidate_path, 'r', encoding='utf-8') as f:
        return f.read()
