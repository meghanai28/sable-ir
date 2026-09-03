import os

def read_report(filename: str, reports_root: str) -> str:
    # Normalize reports_root to absolute path
    reports_root = os.path.abspath(os.path.realpath(reports_root))
    
    # Normalize the candidate path
    candidate = os.path.join(reports_root, filename)
    candidate = os.path.abspath(candidate)
    
    # Check that the normalized path lies within reports_root
    # Use os.path.commonpath for reliable comparison
    try:
        common = os.path.commonpath([candidate, reports_root])
    except ValueError:
        # Different drives on Windows
        raise ValueError("Path escape detected")
    
    if common != reports_root:
        raise ValueError("Path escape detected")
    
    # Inspect every user-selected path component from filename with lstat
    # Split filename into components (skip empty strings from leading/trailing slashes)
    parts = []
    current = filename
    while True:
        head, tail = os.path.split(current)
        if tail:
            parts.append(tail)
        if not head or head == current:
            if head and head != current and head != os.sep:
                parts.append(head)
            break
        current = head
    
    # Reverse to get components in order from root to leaf
    parts = list(reversed(parts))
    
    # If filename is absolute, parts will start with empty string or drive letter
    # We need to check each user-selected component
    # Reconstruct by walking from reports_root
    current_path = reports_root
    for part in parts:
        # Skip empty parts and current directory references at start
        if not part or part == '.':
            continue
        if part == '..':
            # This would be caught by path escape check, but check here too
            raise ValueError("Path escape detected")
        
        next_path = os.path.join(current_path, part)
        
        # Use lstat to check if this component is a symbolic link
        try:
            stat_info = os.lstat(next_path)
        except FileNotFoundError:
            # Component doesn't exist, let the final open handle it
            # But we still need to continue validation for remaining components
            # Actually, if a component doesn't exist, we can't lstat it
            # Break out and let open handle the missing file
            break
        
        # Check if symbolic link
        if os.path.islink(next_path):
            raise ValueError("Symbolic link detected")
        
        current_path = next_path
    
    # Open the validated path, read contents, decode as UTF-8
    with open(candidate, 'rb') as f:
        contents = f.read()
    
    return contents.decode('utf-8')
