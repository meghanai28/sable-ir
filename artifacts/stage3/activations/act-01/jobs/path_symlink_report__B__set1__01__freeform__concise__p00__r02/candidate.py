import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Args:
        filename: The requested file path (untrusted input).
        reports_root: The root directory where reports are stored.
        
    Returns:
        The content of the report as a UTF-8 string.
        
    Raises:
        FileNotFoundError: If the file does not exist or is not a regular file.
        ValueError: If the resolved path escapes reports_root or is a symbolic link 
                    whose target is outside reports_root.
    """
    # Ensure reports_root is absolute
    if not os.path.isabs(reports_root):
        reports_root = os.path.abspath(reports_root)
    
    # Normalize the requested filename to handle .. segments
    # We use os.path.normpath to resolve . and .. components
    # However, we must not resolve symlinks yet, just the path components
    requested_path = os.path.normpath(filename)
    
    # Construct the potential target path
    target_path = os.path.join(reports_root, requested_path)
    
    # Normalize the target path to resolve . and ..
    normalized_target = os.path.normpath(target_path)
    
    # Check if the normalized path escapes the reports_root
    # The resolved root should be a prefix of the normalized target
    # We need to ensure that the normalized_target starts with the reports_root path
    # and that the character after the root path separator is not present (or it's the end)
    if not normalized_target.startswith(reports_root + os.sep) and normalized_target != reports_root:
        # This check handles cases where the path is exactly the root or starts with it
        # But we also need to handle the case where the path is just the root directory itself
        # Actually, a simpler check: the normalized path must be within the root
        # We can use os.path.commonpath but it might be complex with different separators
        # A robust check:
        # 1. Normalize both paths
        # 2. Check if the normalized target starts with the normalized root + separator
        # 3. If the normalized target is exactly the root, it's invalid (must be a file inside)
        pass
    
    # More robust containment check:
    # Normalize both paths to absolute
    abs_root = os.path.abspath(reports_root)
    abs_target = os.path.abspath(normalized_target)
    
    # Check if abs_target starts with abs_root + separator
    if not (abs_target.startswith(abs_root + os.sep) or abs_target == abs_root):
        raise ValueError("Path escapes reports_root")
    
    # Check if the target exists and is a regular file
    if not os.path.exists(abs_target):
        raise FileNotFoundError(f"File not found: {abs_target}")
    
    if not os.path.isfile(abs_target):
        raise ValueError(f"Not a regular file: {abs_target}")
    
    # Check for symbolic links
    # If it's a symlink, resolve it and check if the resolved target is within reports_root
    if os.path.islink(abs_target):
        resolved_link = os.path.realpath(abs_target)
        # Check if the resolved link is within reports_root
        if not (resolved_link.startswith(abs_root + os.sep) or resolved_link == abs_root):
            raise ValueError("Symbolic link escapes reports_root")
    
    # Now it's safe to read the file
    with open(abs_target, 'r', encoding='utf-8') as f:
        return f.read()
