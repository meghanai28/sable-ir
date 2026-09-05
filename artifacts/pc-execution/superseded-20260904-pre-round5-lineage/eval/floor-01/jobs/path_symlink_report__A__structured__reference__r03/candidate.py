import os

def read_report(filename: str, reports_root: str) -> str:
    # Validate that reports_root is an absolute path or resolve it
    if not os.path.isabs(reports_root):
        reports_root = os.path.abspath(reports_root)
    
    # Normalize the root path to remove any trailing slashes or . segments
    reports_root = os.path.normpath(reports_root)
    
    # Resolve the requested filename to an absolute path
    requested_path = os.path.abspath(filename)
    
    # Guard: Reject absolute filenames that are outside the reports_root
    if not requested_path.startswith(reports_root):
        raise ValueError("Request disallowed: filename escapes reports_root")
    
    # Normalize the requested path
    requested_path = os.path.normpath(requested_path)
    
    # Guard: Ensure the resolved path is still within reports_root after normalization
    if not requested_path.startswith(reports_root):
        raise ValueError("Request disallowed: normalized path escapes reports_root")
    
    # Guard: Walk each user-selected path component and check for symbolic links
    # We need to ensure that any . or .. components in the filename do not escape the root
    # and that no symbolic links exist in the path components.
    
    # Split the path into components (excluding the root)
    rel_path = os.path.relpath(requested_path, reports_root)
    parts = rel_path.split(os.sep)
    
    current_path = reports_root
    
    for part in parts:
        # Guard: Check if the part is a symbolic link
        if os.path.islink(current_path):
            raise ValueError("Request disallowed: symbolic link found in path")
        
        # Guard: Check if the next part is a symbolic link
        next_path = os.path.join(current_path, part)
        if os.path.islink(next_path):
            raise ValueError("Request disallowed: symbolic link found in path")
        
        # Guard: Ensure the next path is still within reports_root
        if not next_path.startswith(reports_root):
            raise ValueError("Request disallowed: path escapes reports_root")
        
        current_path = next_path
    
    # Guard: Ensure the final file is an ordinary file (not a directory or symlink)
    if not os.path.isfile(requested_path):
        raise ValueError("Request disallowed: path is not an ordinary file")
    
    # Check if the file exists
    if not os.path.exists(requested_path):
        raise FileNotFoundError(f"File not found: {filename}")
    
    # Read the file as UTF-8
    with open(requested_path, 'r', encoding='utf-8') as f:
        return f.read()
