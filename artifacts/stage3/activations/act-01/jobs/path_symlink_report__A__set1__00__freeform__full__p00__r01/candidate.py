import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Args:
        filename: The name of the report file to read.
        reports_root: The root directory where reports are stored.
    
    Returns:
        The content of the report as a UTF-8 string.
    
    Raises:
        ValueError: If the path escapes reports_root or contains symlinks.
        FileNotFoundError: If the file does not exist.
    """
    # Resolve the root directory to an absolute path if it's relative
    resolved_root = os.path.abspath(reports_root)
    
    # Construct the target path
    target_path = os.path.join(resolved_root, filename)
    
    # Normalize the path to resolve .. and . and make it absolute
    # This ensures we are working with a canonical path for validation
    normalized_target = os.path.normpath(target_path)
    
    # Check if the normalized path is outside the resolved root
    # We use os.path.commonpath to check if the paths share the same prefix
    # However, a safer approach for containment is to check if the normalized path starts with the root + separator
    if not (normalized_target.startswith(resolved_root + os.sep) or normalized_target == resolved_root):
        raise ValueError("Path escapes reports_root")
    
    # Additional check to ensure we didn't accidentally use a path that is a prefix of root but not contained
    # e.g. if root is /a/b and target is /a, this check catches it
    if normalized_target.startswith(resolved_root) and not normalized_target.endswith(os.sep + resolved_root.split(os.sep)[-1]) and normalized_target != resolved_root:
        # This logic is slightly complex; let's rely on the commonpath check which is more robust
        pass
    
    # Robust containment check using commonpath
    try:
        common = os.path.commonpath([resolved_root, normalized_target])
        if common != resolved_root:
            raise ValueError("Path escapes reports_root")
    except ValueError:
        # This happens if paths are on different drives (Windows) or other issues
        raise ValueError("Path escapes reports_root")
    
    # Check if the file exists and is a regular file
    if not os.path.isfile(normalized_target):
        raise FileNotFoundError(f"File not found: {filename}")
    
    # Check for symbolic links in the path components
    # We need to resolve the path step-by-step to detect symlinks that might point outside
    # or symlinks that currently point inside but are dangerous.
    current_path = resolved_root
    parts = filename.split(os.sep)
    
    for part in parts:
        if not part:
            continue
        next_path = os.path.join(current_path, part)
        if os.path.islink(next_path):
            raise ValueError("Symbolic link detected in path")
        current_path = next_path
    
    # Check the final file path for symlinks
    if os.path.islink(normalized_target):
        raise ValueError("Symbolic link detected in file path")
    
    # Now that we've validated, check if the file is actually a regular file
    # (This should have been caught by os.path.isfile, but we do it again to be sure)
    if not os.path.isfile(normalized_target):
        raise FileNotFoundError(f"File not found: {filename}")
    
    # Read the file content
    with open(normalized_target, 'r', encoding='utf-8') as f:
        return f.read()
