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
    
    # Step 3: Derive candidate path by joining reports_root with filename
    # Use lstrip to handle leading separators in filename
    clean_filename = filename.lstrip(os.sep)
    if os.altsep:
        clean_filename = clean_filename.lstrip(os.altsep)
    
    candidate_path = os.path.join(resolved_root, clean_filename)
    
    # Step 4: Resolve candidate path completely, following all symlinks
    try:
        resolved_target = os.path.realpath(candidate_path)
    except (OSError, ValueError):
        raise ValueError("unable to resolve candidate path")
    
    # Step 5: Compare resolved target against resolved root boundary
    # Ensure containment: resolved_target equals resolved_root or starts with resolved_root + separator
    if resolved_target == resolved_root:
        # The target is the root directory itself, which is not a file
        # We still check containment here, but it will fail the file type check later
        pass
    elif not (resolved_target.startswith(resolved_root + os.sep)):
        if os.altsep and not resolved_target.startswith(resolved_root + os.altsep):
            raise ValueError("resolved target escapes the approved root directory")
        elif not os.altsep:
            raise ValueError("resolved target escapes the approved root directory")
    
    # Step 6: Check file type if resolved target exists
    if os.path.lexists(resolved_target):
        try:
            mode = os.stat(resolved_target, follow_symlinks=True).st_mode
        except OSError:
            raise ValueError("unable to stat resolved target")
        
        if not stat.S_ISREG(mode):
            raise ValueError("resolved target is not an ordinary regular file")
    
    # Step 7-9: Open, read, and return file contents
    with open(resolved_target, 'r', encoding='utf-8') as f:
        return f.read()
