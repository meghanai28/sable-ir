import os


def read_report(filename: str, reports_root: str) -> str:
    # Normalize reports_root to absolute path
    reports_root = os.path.abspath(os.path.realpath(reports_root))
    
    # Construct initial path under reports_root
    # Reject absolute paths and paths with parent directory traversal components
    # by checking if the normalized path stays under reports_root
    requested_path = os.path.join(reports_root, filename)
    normalized_path = os.path.normpath(requested_path)
    
    # Check for path traversal via normpath
    if not normalized_path.startswith(reports_root + os.sep) and normalized_path != reports_root:
        raise ValueError("Path escapes reports_root")
    
    # Fully resolve symlinks while rechecking containment
    resolved_path = normalized_path
    while True:
        try:
            # Check if current path is a symlink
            if os.path.islink(resolved_path):
                # Read the symlink target
                link_target = os.readlink(resolved_path)
                
                # Resolve relative symlink targets against the directory containing the symlink
                if not os.path.isabs(link_target):
                    link_dir = os.path.dirname(resolved_path)
                    resolved_link = os.path.normpath(os.path.join(link_dir, link_target))
                else:
                    resolved_link = os.path.normpath(link_target)
                
                # Check if resolved link target stays within reports_root
                real_resolved_link = os.path.realpath(resolved_link)
                if not real_resolved_link.startswith(reports_root + os.sep) and real_resolved_link != reports_root:
                    raise ValueError("Symlink target escapes reports_root")
                
                resolved_path = real_resolved_link
            else:
                # Not a symlink, done resolving
                break
        except OSError:
            # If we can't read the symlink or path doesn't exist, break and let
            # the final check handle it
            break
    
    # Final resolution to catch any remaining symlinks in path components
    final_path = os.path.realpath(resolved_path)
    
    # Verify final resolved path is still within reports_root
    if not final_path.startswith(reports_root + os.sep) and final_path != reports_root:
        raise ValueError("Resolved path escapes reports_root")
    
    # Verify it's a file (not a directory) and exists
    if not os.path.exists(final_path):
        raise FileNotFoundError(f"File not found: {final_path}")
    
    if not os.path.isfile(final_path):
        raise ValueError("Path is not a regular file")
    
    # Read and return UTF-8 content
    with open(final_path, 'r', encoding='utf-8') as f:
        return f.read()
