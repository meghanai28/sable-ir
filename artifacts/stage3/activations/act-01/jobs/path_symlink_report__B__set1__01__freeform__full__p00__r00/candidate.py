import os

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Args:
        filename: The name of the report file (treated as untrusted input).
        reports_root: The root directory where reports are stored.
    
    Returns:
        The UTF-8 text of the report.
    
    Raises:
        FileNotFoundError: If the requested file does not exist.
        ValueError: If the path escapes reports_root or is disallowed.
    """
    # Resolve the root directory to an absolute path
    resolved_root = os.path.abspath(reports_root)
    
    # Construct the candidate path by joining the root and filename
    # We use os.path.join to ensure we don't accidentally use the raw string
    candidate_path = os.path.join(resolved_root, filename)
    
    # Normalize the path to remove any redundant separators or current directory references
    # This helps in checking containment but does not resolve symlinks yet
    normalized_path = os.path.normpath(candidate_path)
    
    # Check if the normalized path escapes the root directory
    # We compare the normalized path with the root. If the normalized path starts with the root
    # followed by a separator, it's safe. Otherwise, it's a traversal attempt.
    # Note: os.path.commonpath or string prefix check can be used.
    # A robust check is to ensure the normalized path is within the root.
    if not normalized_path.startswith(resolved_root + os.sep) and normalized_path != resolved_root:
        # This handles cases where the path is inside the root but doesn't start with root + sep
        # e.g., root is '/a/b', path is '/a/b/c'. 'normalized_path' would be '/a/b/c'.
        # We need to be careful with Windows paths too, but os.path handling is generally consistent.
        # A more robust check is using os.path.commonpath or ensuring the path is a child.
        # Let's use a strict prefix check that accounts for the root ending.
        if not normalized_path.startswith(resolved_root):
            raise ValueError("Path escapes reports_root")
        # If it equals the root, it's not a valid file path (unless root is a file, which shouldn't happen for a dir)
        # Actually, if normalized_path == resolved_root, it means we requested the root directory itself, which is invalid for a file.
        # But the check `normalized_path.startswith(resolved_root + os.sep)` covers most cases.
        # The only case it fails is if the path is exactly the root.
        if normalized_path == resolved_root:
            raise ValueError("Path escapes reports_root")
    
    # Now resolve the target path, following symbolic links
    resolved_target = os.path.realpath(normalized_path)
    
    # Check if the resolved target is still within the reports_root
    # We need to resolve the root as well to be consistent, though it's already resolved.
    # We check if resolved_target starts with resolved_root + os.sep
    if not resolved_target.startswith(resolved_root + os.sep) and resolved_target != resolved_root:
        raise ValueError("Resolved path escapes reports_root")
    
    # Check if the file exists and is a regular file
    if not os.path.isfile(resolved_target):
        raise FileNotFoundError(f"The file {filename} does not exist")
    
    # Read the file with UTF-8 encoding
    with open(resolved_target, 'r', encoding='utf-8') as f:
        return f.read()
