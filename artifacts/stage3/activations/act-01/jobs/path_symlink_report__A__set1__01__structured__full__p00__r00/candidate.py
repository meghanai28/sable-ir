import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Args:
        filename: The requested filename (untrusted).
        reports_root: The root directory for allowed reports.
    
    Returns:
        The content of the report file as a UTF-8 string.
    
    Raises:
        ValueError: If the path escapes reports_root or contains symbolic links.
        FileNotFoundError: If the file does not exist.
    """
    # Resolve the reports_root to an absolute path to ensure consistency
    resolved_root = os.path.abspath(reports_root)
    
    # Construct the full path
    full_path = os.path.abspath(filename)
    
    # Normalize the path to remove any redundant separators or current directory references
    normalized_path = os.path.normpath(full_path)
    
    # Check if the normalized path starts with the resolved root
    # We use os.path.commonpath to verify containment, but we must be careful with trailing slashes
    # A safer approach is to ensure the normalized path is within the root directory
    if not (normalized_path == resolved_root or normalized_path.startswith(resolved_root + os.sep)):
        raise ValueError("Path escapes reports_root")
    
    # Walk each user-selected path component beneath the resolved reports_root
    # This ensures that even if the path is deep, we validate the entire chain
    # We split the path into components relative to the root to check each step
    try:
        # Get the relative path from the root
        relative_path = os.path.relpath(normalized_path, resolved_root)
        
        # Split the relative path into components
        parts = relative_path.split(os.sep)
        
        # Check each component for symbolic links
        current_path = resolved_root
        for part in parts:
            # Resolve the path to check for symlinks
            resolved_part = os.path.normpath(os.path.join(current_path, part))
            
            # Check if the resolved part is a symbolic link
            if os.path.islink(resolved_part):
                raise ValueError("Symbolic link detected in path")
            
            # Update current_path for the next iteration
            current_path = resolved_part
        
        # Ensure the final path is within the root (re-checking just in case)
        if not (normalized_path == resolved_root or normalized_path.startswith(resolved_root + os.sep)):
            raise ValueError("Path escapes reports_root")
            
    except ValueError:
        raise
    
    # Check if the file exists and is a regular file
    if not os.path.isfile(normalized_path):
        raise FileNotFoundError(f"File not found: {filename}")
    
    # Read the file content
    with open(normalized_path, 'r', encoding='utf-8') as f:
        return f.read()
