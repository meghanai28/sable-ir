import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Args:
        filename: The name of the report file to read.
        reports_root: The root directory containing the reports.
    
    Returns:
        The content of the report file as a UTF-8 string.
    
    Raises:
        ValueError: If the resolved path escapes reports_root or contains a symbolic link.
        FileNotFoundError: If the file does not exist or is not a regular file.
    """
    # Resolve the reports_root to an absolute path
    resolved_root = os.path.abspath(reports_root)
    
    # Resolve the requested filename to an absolute path
    resolved_filename = os.path.abspath(filename)
    
    # Normalize the resolved filename to remove any redundant separators or current directory references
    normalized_filename = os.path.normpath(resolved_filename)
    
    # Check if the normalized path is within the reports_root
    # We use os.path.commonpath to ensure the path is strictly under reports_root
    try:
        common_path = os.path.commonpath([resolved_root, normalized_filename])
        if common_path != resolved_root:
            raise ValueError("The requested path is outside the allowed directory.")
    except ValueError as e:
        # This can happen if paths are on different drives (Windows) or have other issues
        raise ValueError("The requested path is outside the allowed directory.") from e
    
    # Check for symbolic links in the path components
    # We need to check the path components from the root down to the filename
    # Split the normalized path into components, excluding the root itself
    parts = normalized_filename.split(os.sep)
    current_path = resolved_root
    
    for i, part in enumerate(parts):
        if part == '':
            continue
            
        next_path = os.path.join(current_path, part)
        
        # Check if the next path exists and if it's a symlink
        if os.path.lexists(next_path):
            # Check if it's a symlink
            if os.path.islink(next_path):
                raise ValueError("Symbolic link detected in the path.")
            
            # If it's not a symlink, we still need to check its components for symlinks
            # But since we are walking up, we should check the parent directory for symlinks
            # Actually, the requirement says "walk each user-selected path component beneath the resolved reports_root"
            # So we check each component from root to the file
            pass
        
        current_path = next_path
    
    # Final check to ensure the file is a regular file and exists
    if not os.path.isfile(normalized_filename):
        raise FileNotFoundError(f"The file '{filename}' does not exist or is not a regular file.")
    
    # Read the file
    with open(normalized_filename, 'r', encoding='utf-8') as f:
        return f.read()
