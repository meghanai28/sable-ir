import os


def read_report(filename: str, reports_root: str) -> str:
    # Step 1: Join filename to reports_root and resolve to an absolute path
    reports_root = os.path.abspath(reports_root)
    joined_path = os.path.join(reports_root, filename)
    resolved_path = os.path.abspath(joined_path)

    # Step 2: Validate the resolved path remains strictly inside reports_root
    # Use os.path.commonpath for proper path comparison
    try:
        common = os.path.commonpath([resolved_path, reports_root])
    except ValueError:
        # On Windows, paths on different drives raise ValueError
        raise ValueError("Path escapes approved root directory")
    
    if common != reports_root:
        raise ValueError("Path escapes approved root directory")

    # Step 3: Check each user-selected path component for symlink status and reject if present
    # Split the filename into its components (user-selected parts)
    # We need to check each component of the user input for symlinks in the path traversal
    
    # Normalize the filename to get clean components
    normalized_filename = os.path.normpath(filename)
    
    # Build up the path component by component and check for symlinks
    current_path = reports_root
    parts = normalized_filename.split(os.sep)
    
    # Filter out empty parts and '.' (current directory)
    # '..' is kept because we need to check it too, though it would be in the resolved path
    filtered_parts = []
    for part in parts:
        if part == '' or part == '.':
            continue
        filtered_parts.append(part)
    
    for part in filtered_parts:
        current_path = os.path.join(current_path, part)
        # Check if this specific path component location is a symlink
        # We check with os.path.islink which returns True for symlinks
        # Need to check if the path exists and is a symlink
        if os.path.islink(current_path):
            raise ValueError("Symbolic link encountered in path")
        # Also check if any parent path component that exists is a symlink
        # Actually, we need to check all components, so we do it step by step
    
    # Additional check: verify no symlinks in any existing component of the resolved path
    # The loop above checks components as we build them, but we need to be thorough
    
    # Re-verify by checking each component of the resolved path under reports_root
    rel_path = os.path.relpath(resolved_path, reports_root)
    if rel_path == '.':
        # This means filename resolved to reports_root itself, which is a directory
        raise ValueError("Target is not an ordinary file")
    
    rel_parts = rel_path.split(os.sep)
    check_path = reports_root
    for part in rel_parts:
        check_path = os.path.join(check_path, part)
        # At each step, if the path exists, check if it's a symlink
        if os.path.islink(check_path):
            raise ValueError("Symbolic link encountered in path")

    # Step 4: Verify the target exists as an ordinary file
    if not os.path.exists(resolved_path):
        raise FileNotFoundError(f"File not found: {resolved_path}")
    
    if not os.path.isfile(resolved_path):
        raise ValueError("Target is not an ordinary file")
    
    # Final symlink check on the resolved path itself
    if os.path.islink(resolved_path):
        raise ValueError("Symbolic link encountered in path")

    # Step 5: Open in UTF-8 text mode and read contents
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
