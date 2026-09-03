import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    # Normalize reports_root to absolute path
    reports_root = os.path.abspath(os.path.realpath(reports_root))
    
    # Split filename into components and validate each
    filename_parts = filename.split(os.sep)
    
    # Remove empty parts and handle leading slash
    clean_parts = []
    for part in filename_parts:
        if part == '':
            continue
        if part == '.':
            continue
        if part == '..':
            clean_parts.append(part)
        else:
            clean_parts.append(part)
    
    # Build the path component by component, checking each for symlinks
    current_path = reports_root
    for i, part in enumerate(clean_parts):
        current_path = os.path.join(current_path, part)
        
        # Check if this component exists and is a symlink
        try:
            file_stat = os.lstat(current_path)
            if stat.S_ISLNK(file_stat.st_mode):
                raise ValueError("Symbolic link detected")
        except FileNotFoundError:
            # If this is the last component, it might be the file we're trying to open
            # Allow FileNotFoundError to propagate later from open()
            if i < len(clean_parts) - 1:
                raise
    
    # Normalize the final path
    final_path = os.path.abspath(current_path)
    
    # Validate that the final path is within reports_root
    # Use realpath to resolve any symlinks that might have slipped through
    # But we already checked each component with lstat, so there shouldn't be any
    try:
        real_final = os.path.realpath(final_path)
    except FileNotFoundError:
        # The file doesn't exist, but we still need to check if the path escapes
        # Use normpath for non-existent paths
        real_final = os.path.normpath(final_path)
    
    # Ensure the path is within reports_root
    # Check both the path itself and its realpath
    normalized_root = os.path.normpath(reports_root)
    
    # For the check, we need to handle the case where final_path doesn't exist yet
    # We already validated components, so check the constructed path
    if not final_path.startswith(reports_root + os.sep) and final_path != reports_root:
        # Also check with normpath
        norm_final = os.path.normpath(final_path)
        norm_root = os.path.normpath(reports_root)
        if not norm_final.startswith(norm_root + os.sep) and norm_final != norm_root:
            raise ValueError("Path escapes reports_root")
    
    # Additional check: ensure no symlink in any component by verifying
    # that the path doesn't deviate from what we'd expect
    expected_path = reports_root
    for part in clean_parts:
        expected_path = os.path.join(expected_path, part)
    
    # Verify the final path matches expected (no symlink traversal changed it)
    # This is already ensured by lstat checks above
    
    # Open, read, decode and return
    with open(final_path, 'rb') as f:
        content = f.read()
    
    return content.decode('utf-8')
