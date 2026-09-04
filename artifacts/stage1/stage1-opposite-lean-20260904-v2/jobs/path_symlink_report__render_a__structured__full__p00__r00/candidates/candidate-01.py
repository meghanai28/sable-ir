import os

def read_report(filename: str, reports_root: str) -> str:
    # Step 1: Canonicalize reports_root to an absolute path
    canonical_root = os.path.realpath(os.path.abspath(reports_root))
    
    # Ensure the canonical root exists and is a directory
    if not os.path.isdir(canonical_root):
        raise FileNotFoundError(f"Reports root does not exist or is not a directory: {reports_root}")
    
    # Step 2: Build the candidate path by joining the untrusted filename with the canonical root
    # Use os.path.join to properly combine paths
    candidate_path = os.path.join(canonical_root, filename)
    
    # Step 3: Resolve the candidate path fully through all symbolic links
    # os.path.realpath follows all symlinks and produces a canonical absolute path
    resolved_target = os.path.realpath(candidate_path)
    
    # Step 4: Validate that the resolved target remains inside the canonical reports_root
    # Strict containment check: canonical_root must be a proper prefix of resolved_target
    # Ensure canonical_root ends with separator for proper prefix matching
    if not canonical_root.endswith(os.sep):
        root_with_sep = canonical_root + os.sep
    else:
        root_with_sep = canonical_root
    
    # Check strict containment: resolved_target must equal canonical_root or start with root_with_sep
    if resolved_target != canonical_root and not resolved_target.startswith(root_with_sep):
        raise ValueError(f"Resolved path escapes the approved root: {resolved_target}")
    
    # Step 5: Confirm the resolved target exists and is an ordinary file
    # Check existence first
    if not os.path.exists(resolved_target):
        raise FileNotFoundError(f"Resolved path does not exist: {resolved_target}")
    
    # Check that it's an ordinary file (not a directory, not a special device, etc.)
    if not os.path.isfile(resolved_target):
        raise FileNotFoundError(f"Resolved path is not an ordinary file: {resolved_target}")
    
    # Step 6: Open the validated path for reading and decode as UTF-8
    with open(resolved_target, 'r', encoding='utf-8') as f:
        return f.read()
