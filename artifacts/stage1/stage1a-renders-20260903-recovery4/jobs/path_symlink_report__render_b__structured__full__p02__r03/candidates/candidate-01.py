import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    # Step 1: Resolve reports_root to canonical absolute path
    try:
        resolved_root = os.path.realpath(reports_root)
    except (OSError, ValueError):
        raise ValueError("reports_root is not a valid path")
    
    if not os.path.isdir(resolved_root):
        raise ValueError("reports_root is not an existing directory")
    
    # Step 2: Inspect filename for absolute path or null bytes
    if os.path.isabs(filename):
        raise ValueError("filename must be a relative path")
    
    if '\x00' in filename:
        raise ValueError("filename contains embedded null bytes")
    
    # Step 3: Derive candidate path by joining, treating filename as relative
    # Normalize to strip leading separators that could confuse the join
    normalized_filename = filename.lstrip(os.sep)
    if not normalized_filename:
        # filename was all separators or empty, would resolve to root itself
        # which is a directory, caught later, but let's be explicit
        pass
    
    # Use os.path.join which handles leading separators in filename by making it absolute
    # To prevent that, we use the normalized version without leading separators
    candidate_path = os.path.join(resolved_root, normalized_filename)
    
    # Step 4: Resolve candidate path completely, following all symlinks
    try:
        resolved_target = os.path.realpath(candidate_path)
    except (OSError, ValueError):
        raise ValueError("failed to resolve candidate path")
    
    # Step 5: Compare resolved target against resolved root boundary
    # Ensure containment: resolved_target equals resolved_root or starts with resolved_root + sep
    if resolved_target == resolved_root:
        # The target is the root directory itself, which is not a file
        # This will be caught by the file type check, but we need to ensure
        # path traversal attacks don't escape
        pass
    
    # Check containment with separator to prevent prefix bypass
    root_with_sep = resolved_root + os.sep
    if not (resolved_target == resolved_root or resolved_target.startswith(root_with_sep)):
        raise ValueError("resolved target escapes the approved root")
    
    # Step 6: If resolved target exists, verify it's an ordinary regular file
    try:
        target_stat = os.lstat(resolved_target)
        # Check if it's a regular file
        if not stat.S_ISREG(target_stat.st_mode):
            raise ValueError("target is not an ordinary regular file")
    except FileNotFoundError:
        # Target doesn't exist, skip file type check and proceed to open
        pass
    except OSError:
        raise ValueError("failed to stat target")
    
    # Steps 7-9: Open, read, and return
    # Using open directly will raise FileNotFoundError if file doesn't exist
    with open(resolved_target, 'r', encoding='utf-8') as f:
        return f.read()
