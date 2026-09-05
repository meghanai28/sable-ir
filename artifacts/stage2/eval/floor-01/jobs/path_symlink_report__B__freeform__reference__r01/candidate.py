import os

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Args:
        filename: The name of the report file to read.
        reports_root: The root directory where the report should be located.
    
    Returns:
        The content of the report file as a UTF-8 string.
    
    Raises:
        FileNotFoundError: If the file does not exist or is not an ordinary file.
        ValueError: If the resolved path escapes the reports_root directory.
    """
    # Normalize the root directory to an absolute path
    resolved_root = os.path.abspath(reports_root)
    
    # Construct the full path by joining the root with the filename
    # This allows the path to be absolute, relative, or contain .. segments
    requested_path = os.path.join(resolved_root, filename)
    
    # Normalize the requested path to resolve .. and . segments
    # This ensures we are working with a clean path representation
    normalized_path = os.path.normpath(requested_path)
    
    # Check if the normalized path escapes the root directory
    # The normalized path must start with the root directory (possibly with a trailing slash)
    if not (normalized_path.startswith(resolved_root + os.sep) or normalized_path == resolved_root):
        raise ValueError("Requested path escapes the reports_root directory")
    
    # Resolve the complete target path, following symbolic links
    # We need to check the resolved path for containment as well
    resolved_target = os.path.realpath(normalized_path)
    
    # Check if the resolved target remains inside reports_root
    # This prevents access to files outside the root even if a symlink is used
    if not (resolved_target.startswith(resolved_root + os.sep) or resolved_target == resolved_root):
        raise ValueError("Resolved target escapes the reports_root directory")
    
    # Check if the file exists and is an ordinary file
    if not os.path.isfile(resolved_target):
        raise FileNotFoundError(f"The file '{filename}' does not exist or is not an ordinary file")
    
    # Read and return the UTF-8 text of the validated report
    with open(resolved_target, 'r', encoding='utf-8') as f:
        return f.read()
