import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    # Step 1: Join filename to reports_root and resolve to an absolute path
    reports_root = os.path.abspath(os.path.realpath(reports_root))
    joined_path = os.path.join(reports_root, filename)
    resolved_path = os.path.abspath(os.path.realpath(joined_path))
    
    # Step 2: Validate the resolved path remains strictly inside reports_root
    if not (resolved_path == reports_root or resolved_path.startswith(reports_root + os.sep)):
        raise ValueError("Path escapes the approved root directory")
    
    # Step 3: Check each user-selected path component for symlink status and reject if present
    # Split the filename into components and walk from reports_root
    if filename:
        filename_parts = filename.split(os.sep)
        # Filter out empty strings from leading/trailing slashes or consecutive slashes
        filename_parts = [p for p in filename_parts if p and p != '.']
        
        current_path = reports_root
        for part in filename_parts:
            current_path = os.path.join(current_path, part)
            # Check if this specific path component location is a symlink
            # We check the path as constructed, before final resolution
            if os.path.islink(current_path):
                raise ValueError("Symbolic link encountered in path")
    
    # Step 4: Verify the target exists as an ordinary file
    try:
        file_stat = os.lstat(resolved_path)
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {resolved_path}")
    
    if not stat.S_ISREG(file_stat.st_mode):
        raise ValueError("Target is not an ordinary file")
    
    # Step 5: Open in UTF-8 text mode and read contents
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
