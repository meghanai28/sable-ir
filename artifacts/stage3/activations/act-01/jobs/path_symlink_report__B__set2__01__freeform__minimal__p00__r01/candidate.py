import os

def read_report(filename: str, reports_root: str) -> str:
    # Resolve the base directory
    reports_root_resolved = os.path.realpath(reports_root)
    
    # Construct the full path
    full_path = os.path.join(reports_root, filename)
    
    # Normalize the path to remove . and .. components
    normalized_path = os.path.normpath(full_path)
    
    # Check if the normalized path escapes the reports_root directory
    # We compare the directory part of the normalized path with reports_root_resolved
    if not normalized_path.startswith(reports_root_resolved + os.sep):
        # Special case: if normalized_path equals reports_root_resolved exactly (e.g., if filename is empty or just "..")
        if normalized_path != reports_root_resolved:
            raise ValueError("Request disallowed: path escapes reports_root")
    
    # Check if the file exists and is a regular file (not a directory)
    if not os.path.isfile(normalized_path):
        raise FileNotFoundError(f"File not found: {normalized_path}")
    
    # Resolve the symbolic link's destination
    resolved_path = os.path.realpath(normalized_path)
    
    # Check if the resolved path escapes the reports_root directory
    if not resolved_path.startswith(reports_root_resolved + os.sep):
        if resolved_path != reports_root_resolved:
            raise ValueError("Request disallowed: symbolic link escapes reports_root")
    
    # Read the file
    with open(normalized_path, 'r', encoding='utf-8') as f:
        return f.read()
