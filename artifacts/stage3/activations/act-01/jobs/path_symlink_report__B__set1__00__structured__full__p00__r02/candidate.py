import os

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Args:
        filename: The name of the file to read (untrusted input).
        reports_root: The root directory where reports are stored.
    
    Returns:
        The UTF-8 text content of the report file.
    
    Raises:
        FileNotFoundError: If the requested file does not exist or is not a regular file.
        ValueError: If the requested path escapes the reports_root directory.
    """
    # Construct the intended target path by joining filename with reports_root
    target_path = os.path.join(reports_root, filename)
    
    # Normalize the path to remove any .. segments or redundant separators
    # This ensures we are working with a canonicalized version of the input
    normalized_path = os.path.normpath(target_path)
    
    # Resolve the full target path, following symbolic links
    # This is critical for the GUARD requirement to check if the link target escapes the root
    resolved_target = os.path.realpath(normalized_path)
    
    # Resolve the root directory as well to ensure consistent comparison
    resolved_root = os.path.realpath(reports_root)
    
    # Check if the resolved target is outside the resolved root
    # os.path.commonpath ensures the path is relative to the root for comparison
    # We use os.path.commonpath to verify the resolved path is within the root directory
    if not resolved_target.startswith(resolved_root + os.sep) and resolved_target != resolved_root:
        raise ValueError("Access denied: Path escapes reports_root")
    
    # Check if the file exists and is a regular file
    if not os.path.isfile(resolved_target):
        raise FileNotFoundError(f"File not found: {resolved_target}")
    
    # Read and return the UTF-8 content
    with open(resolved_target, 'r', encoding='utf-8') as f:
        return f.read()
