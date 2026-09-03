import os

def read_report(filename: str, reports_root: str) -> str:
    # Normalize reports_root to absolute path
    reports_root = os.path.realpath(os.path.abspath(reports_root))
    
    # Construct initial path under reports_root
    requested_path = os.path.join(reports_root, filename)
    
    # Fully resolve symlinks while checking containment
    current_path = requested_path
    visited = set()
    
    while True:
        # Normalize current path
        current_path = os.path.normpath(current_path)
        
        # Check for symlink loops
        if current_path in visited:
            raise ValueError("Symlink loop detected")
        visited.add(current_path)
        
        # Check if current path is within reports_root
        real_current = os.path.realpath(current_path)
        real_reports_root = os.path.realpath(reports_root)
        
        # Ensure the path is under reports_root (with trailing slash check to prevent prefix attacks)
        if not (real_current == real_reports_root or real_current.startswith(real_reports_root + os.sep)):
            raise ValueError("Path escapes approved root")
        
        # Check if current path is a symlink
        if os.path.islink(current_path):
            # Read the symlink target
            link_target = os.readlink(current_path)
            
            # Resolve relative symlink targets relative to the symlink's directory
            if not os.path.isabs(link_target):
                link_dir = os.path.dirname(current_path)
                current_path = os.path.join(link_dir, link_target)
            else:
                current_path = link_target
            
            # Continue to resolve the new path
            continue
        
        # Not a symlink, we have our final resolved path
        break
    
    # Final resolved path after all symlinks
    final_path = os.path.realpath(current_path)
    
    # Final containment check
    if not (final_path == real_reports_root or final_path.startswith(real_reports_root + os.sep)):
        raise ValueError("Resolved path escapes approved root")
    
    # Verify it's a file (not a directory)
    if os.path.exists(final_path) and not os.path.isfile(final_path):
        raise ValueError("Not an ordinary file")
    
    # Read and return UTF-8 content
    with open(final_path, 'r', encoding='utf-8') as f:
        return f.read()
