import os

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Args:
        filename: Untrusted input filename.
        reports_root: Root directory where the report should be located.
    
    Returns:
        The UTF-8 text content of the validated report.
    
    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the path escapes reports_root or follows a link to an outside location.
    """
    # Resolve the root directory to an absolute path
    resolved_root = os.path.abspath(reports_root)
    
    # Construct the full path by joining the root and filename
    # We must ensure the filename is not absolute and doesn't start with ..
    if os.path.isabs(filename):
        raise ValueError("Filename must not be an absolute path")
    
    # Join the root and filename to create the candidate path
    candidate_path = os.path.join(resolved_root, filename)
    
    # Normalize the path to resolve any .. or . segments
    normalized_path = os.path.normpath(candidate_path)
    
    # Check if the normalized path is within the resolved root
    # We use os.path.commonpath to ensure the path is strictly inside
    try:
        common = os.path.commonpath([resolved_root, normalized_path])
        if common != resolved_root:
            raise ValueError("Path escapes reports_root")
    except ValueError:
        raise ValueError("Invalid path structure")
    
    # Check if the path is a directory
    if os.path.isdir(normalized_path):
        raise ValueError("Requested path is a directory")
    
    # Check if the file exists
    if not os.path.isfile(normalized_path):
        raise FileNotFoundError(f"File not found: {filename}")
    
    # Check for symbolic links and ensure they don't escape the root
    if os.path.islink(normalized_path):
        link_target = os.path.realpath(normalized_path)
        # Ensure the resolved target is still within the reports_root
        if not link_target.startswith(resolved_root + os.sep) and link_target != resolved_root:
            raise ValueError("Symbolic link escapes reports_root")
        # Even if inside, we must not follow the link to read the file
        # The requirement states: "a link whose resolved target is inside the directory is still not acceptable"
        raise ValueError("Symbolic links are not allowed")
    
    # Read the file content
    with open(normalized_path, 'r', encoding='utf-8') as f:
        return f.read()
