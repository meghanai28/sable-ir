import os

def read_report(filename: str, reports_root: str) -> str:
    # Resolve and validate reports_root
    real_reports_root = os.path.realpath(reports_root)
    if not os.path.isdir(real_reports_root):
        raise ValueError("reports_root is not a valid directory")
    
    # Construct the requested path
    requested_path = os.path.join(real_reports_root, filename)
    
    # Check for path traversal beyond reports_root
    real_requested_path = os.path.realpath(requested_path)
    if not real_requested_path.startswith(real_reports_root + os.sep) and real_requested_path != real_reports_root:
        raise ValueError("path traversal detected")
    
    # Check each user-selected path component for symbolic links
    # Split the filename into components and check each one
    current_path = real_reports_root
    # Normalize filename to handle . and .. consistently
    normalized_filename = os.path.normpath(filename)
    if normalized_filename.startswith('..') or normalized_filename.startswith('/'):
        raise ValueError("invalid path components")
    
    parts = normalized_filename.split(os.sep)
    for part in parts:
        if part == '' or part == '.':
            continue
        current_path = os.path.join(current_path, part)
        # Check if any component in the path (as constructed by user input) is a symlink
        # We check the path as it would be resolved step by step
        if os.path.islink(current_path):
            raise ValueError("symbolic link detected in path")
        # Also check if the path component exists before continuing
        if not os.path.exists(current_path):
            # Let it fall through to the final check for FileNotFoundError
            break
    
    # Final validation: must be a regular file (not a symlink, not a directory)
    if not os.path.exists(real_requested_path):
        raise FileNotFoundError(f"file not found: {filename}")
    
    if not os.path.isfile(real_requested_path):
        raise ValueError("not a regular file")
    
    # Additional safety: verify the realpath doesn't have symlink components we missed
    # by checking if realpath matches what we'd expect from non-symlink traversal
    if os.path.islink(real_requested_path):
        raise ValueError("symbolic link detected")
    
    # Read and return the file contents as UTF-8
    with open(real_requested_path, 'r', encoding='utf-8') as f:
        return f.read()
