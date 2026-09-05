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
        FileNotFoundError: If the file does not exist or is not a regular file.
        ValueError: If the path escapes reports_root or contains symbolic links.
    """
    # Resolve the root directory to an absolute path
    resolved_root = os.path.abspath(reports_root)
    
    # Resolve the requested filename to an absolute path
    resolved_filename = os.path.abspath(filename)
    
    # Normalize the path to remove any redundant separators or current directory references
    normalized_filename = os.path.normpath(resolved_filename)
    
    # Check if the normalized path is within the reports_root
    # We need to ensure that the normalized path is a child of the resolved root
    if not normalized_filename.startswith(resolved_root + os.sep) and normalized_filename != resolved_root:
        raise ValueError("Path escapes reports_root")
    
    # Check if the file exists and is a regular file
    if not os.path.isfile(normalized_filename):
        raise FileNotFoundError(f"The file {filename} does not exist")
    
    # Check for symbolic links in the path components
    # We walk up the path components to ensure no symbolic links are present
    parts = normalized_filename.split(os.sep)
    current_path = ""
    
    for part in parts:
        if not part:
            continue
        current_path = os.path.join(current_path, part)
        
        # If the path is the root, skip checking
        if current_path == resolved_root:
            continue
            
        # Check if the current path is a symbolic link
        if os.path.islink(current_path):
            raise ValueError(f"Symbolic link found in path: {current_path}")
        
        # Check if the file exists at this point (for intermediate directories)
        if os.path.isdir(current_path):
            pass  # Directory check is fine
        elif os.path.isfile(current_path):
            pass  # File check is fine
        else:
            # If it's not a directory or file, it might be a broken link or other issue
            # But we already checked islink, so this should be safe
            pass
    
    # Read the file content
    try:
        with open(normalized_filename, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        raise

    # Final containment check after normalization
    # Ensure the final resolved path is still within the root
    if not normalized_filename.startswith(resolved_root + os.sep) and normalized_filename != resolved_root:
        raise ValueError("Path escapes reports_root")
