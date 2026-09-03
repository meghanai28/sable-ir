import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    # Normalize reports_root to absolute path
    reports_root = os.path.abspath(reports_root)
    
    # Split filename into components and validate no absolute path or parent directory references
    # at the string level
    if os.path.isabs(filename):
        raise ValueError("Absolute paths are not allowed")
    
    # Split into components for inspection
    parts = filename.split(os.sep)
    
    # Filter out empty parts and current directory references
    parts = [p for p in parts if p and p != '.']
    
    # Check for parent directory references
    if '..' in parts:
        raise ValueError("Parent directory references are not allowed")
    
    # Build the path step by step, checking each component with lstat for symlinks
    current_path = reports_root
    for part in parts:
        current_path = os.path.join(current_path, part)
        try:
            file_stat = os.lstat(current_path)
        except FileNotFoundError:
            # Component doesn't exist yet, which is fine for intermediate paths
            # if the final path doesn't exist, open() will raise FileNotFoundError
            continue
        
        # Check if this component is a symbolic link
        if stat.S_ISLNK(file_stat.st_mode):
            raise ValueError("Symbolic links are not allowed")
    
    # Final path validation: normalize and check it's within reports_root
    final_path = os.path.abspath(os.path.join(reports_root, filename))
    
    # Ensure the path is within reports_root
    try:
        relative = os.path.relpath(final_path, reports_root)
    except ValueError:
        raise ValueError("Path escapes the reports root")
    
    if relative.startswith('..'):
        raise ValueError("Path escapes the reports root")
    
    if os.path.commonpath([final_path, reports_root]) != reports_root:
        raise ValueError("Path escapes the reports root")
    
    # Verify the final resolved path is not a symlink (defense in depth)
    try:
        final_stat = os.lstat(final_path)
        if stat.S_ISLNK(final_stat.st_mode):
            raise ValueError("Symbolic links are not allowed")
    except FileNotFoundError:
        # File doesn't exist, let open() handle it
        pass
    
    # Open, read, decode as UTF-8, and return
    with open(final_path, 'rb') as f:
        contents = f.read()
    
    return contents.decode('utf-8')
