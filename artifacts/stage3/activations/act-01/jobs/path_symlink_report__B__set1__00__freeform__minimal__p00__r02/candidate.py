import os

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Args:
        filename: The name of the report file to read.
        reports_root: The root directory where reports are stored.
    
    Returns:
        The UTF-8 text of the report.
    
    Raises:
        FileNotFoundError: If the file does not exist or is not a regular file.
        ValueError: If the path escapes reports_root or if the request is disallowed.
    """
    # Construct the base path for the report
    base_path = os.path.join(reports_root, filename)
    
    # Normalize the path to remove redundant separators and resolve relative components
    # This helps in detecting escape attempts like '../'
    normalized_base = os.path.normpath(base_path)
    
    # Check if the normalized path starts with the reports_root
    # We need to handle the case where reports_root might have trailing slashes or not
    root_normalized = os.path.normpath(reports_root)
    
    # Ensure the normalized path is within the root
    if not normalized_base.startswith(root_normalized + os.sep) and normalized_base != root_normalized:
        raise ValueError("Path escapes reports_root")
    
    # Resolve the full path, following symbolic links
    # os.path.realpath resolves symlinks and normalizes the path
    resolved_path = os.path.realpath(normalized_base)
    
    # Check if the resolved path is still within the reports_root
    # We use the same logic as above for the resolved path
    if not resolved_path.startswith(root_normalized + os.sep) and resolved_path != root_normalized:
        raise ValueError("Resolved path escapes reports_root")
    
    # Check if the file exists and is a regular file
    if not os.path.isfile(resolved_path):
        raise FileNotFoundError(f"The file {filename} does not exist or is not a regular file")
    
    # Read the file with UTF-8 encoding
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
