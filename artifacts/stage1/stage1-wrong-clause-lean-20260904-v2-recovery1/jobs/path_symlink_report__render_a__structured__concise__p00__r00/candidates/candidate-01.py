import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    # Step 1: Join filename to reports_root and resolve to an absolute path
    reports_root = os.path.abspath(os.path.realpath(reports_root))
    requested_path = os.path.join(reports_root, filename)
    resolved_path = os.path.abspath(os.path.realpath(requested_path))
    
    # Step 2: Validate strict containment under reports_root
    # Check the resolved path itself
    if not _is_contained(resolved_path, reports_root):
        raise ValueError("Path escapes reports_root")
    
    # Check for symlink components in the original path
    # We need to validate any intermediate symlinks as well
    current_path = reports_root
    remaining = filename
    
    # Normalize and split the filename
    parts = []
    for part in remaining.replace('\\', '/').split('/'):
        if part == '' or part == '.':
            continue
        elif part == '..':
            if parts:
                parts.pop()
        else:
            parts.append(part)
    
    # Walk through each component to check symlinks
    for part in parts:
        current_path = os.path.join(current_path, part)
        if os.path.islink(current_path):
            link_target = os.readlink(current_path)
            # Resolve relative link targets
            if not os.path.isabs(link_target):
                link_target = os.path.join(os.path.dirname(current_path), link_target)
            link_target = os.path.abspath(os.path.realpath(link_target))
            if not _is_contained(link_target, reports_root):
                raise ValueError("Symlink target escapes reports_root")
    
    # Final validation after resolving all symlinks
    if not _is_contained(resolved_path, reports_root):
        raise ValueError("Path escapes reports_root")
    
    # Step 3: Verify target exists as an ordinary file
    if not os.path.exists(resolved_path):
        raise FileNotFoundError(f"File not found: {resolved_path}")
    
    if not os.path.isfile(resolved_path):
        raise ValueError("Target is not an ordinary file")
    
    # Check for special file types using stat
    file_stat = os.lstat(resolved_path)
    mode = file_stat.st_mode
    
    # Reject if not a regular file (shouldn't happen after isfile, but defense in depth)
    if not stat.S_ISREG(mode):
        raise ValueError("Target is not an ordinary file")
    
    # Reject device files and other special entries
    if stat.S_ISBLK(mode) or stat.S_ISCHR(mode) or stat.S_ISFIFO(mode) or stat.S_ISSOCK(mode):
        raise ValueError("Target is a special file")
    
    # Step 4: Open in UTF-8 text mode and read contents
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()

def _is_contained(path: str, root: str) -> bool:
    """Check if path is strictly contained within root."""
    # Ensure both paths are absolute and normalized
    path = os.path.abspath(path)
    root = os.path.abspath(root)
    
    # Add trailing separator to root to prevent prefix attacks
    # e.g., /foo/bar matching /foo/barbaz
    if not root.endswith(os.sep):
        root_with_sep = root + os.sep
    else:
        root_with_sep = root
    
    return path == root or path.startswith(root_with_sep)
