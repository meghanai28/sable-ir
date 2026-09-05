import os
import re

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Security checks applied:
    1. Rejects symbolic links in the path traversal.
    2. Validates the resolved path stays within reports_root.
    3. Rejects non-ordinary files (directories, device files, etc.).
    4. Raises FileNotFoundError for missing files.
    5. Raises ValueError if the path is outside the allowed root or contains unsafe components.
    """
    # Normalize the root directory to an absolute path
    root = os.path.abspath(reports_root)
    
    # Construct the target path
    target = os.path.abspath(filename)
    
    # Security Check 1: Ensure the target is within the root
    # This prevents directory traversal even if filename is manipulated
    if not target.startswith(root + os.sep) and target != root:
        raise ValueError("Access denied: Path is outside the approved filesystem root.")
    
    # Security Check 2: Resolve the path to check for symbolic links
    # We need to resolve the path but not follow the link itself yet
    # However, the requirement says "reject if any user-selected path component is a symbolic link"
    # We will check the link status of the file components
    
    # First, check if the final path is a symlink
    if os.path.islink(target):
        raise ValueError("Access denied: Symbolic link detected in path.")
    
    # Check if the parent directory is a symlink (to prevent traversal via parents)
    # We walk up from the target to root checking each component
    current = target
    while current != root and current != os.path.dirname(current):
        parent = os.path.dirname(current)
        if os.path.islink(parent):
            raise ValueError("Access denied: Symbolic link detected in path component.")
        current = parent
    
    # Check if the file exists and is an ordinary file
    if not os.path.isfile(target):
        raise FileNotFoundError(f"File not found: {filename}")
    
    # Additional check: Ensure it's not a special file (like device, socket, etc.)
    # os.path.isfile already handles most, but let's be explicit about device files
    if os.path.islink(target) or not os.path.isfile(target):
        raise ValueError("Access denied: Only ordinary files are allowed.")
    
    # Read the file content
    with open(target, 'r', encoding='utf-8') as f:
        return f.read()
