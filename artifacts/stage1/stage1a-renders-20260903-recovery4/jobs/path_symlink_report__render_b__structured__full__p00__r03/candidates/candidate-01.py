import os

def read_report(filename: str, reports_root: str) -> str:
    # Step 1: Canonicalize reports_root to an absolute path
    canonical_root = os.path.realpath(os.path.abspath(reports_root))
    
    # Step 2: Build the candidate path by joining the untrusted filename with the canonical root
    candidate_path = os.path.join(canonical_root, filename)
    
    # Step 3: Resolve the candidate path fully through all symbolic links
    resolved_target = os.path.realpath(candidate_path)
    
    # Step 4: Validate that the resolved target remains inside the canonical reports_root
    # Ensure canonical_root ends with separator for strict prefix check
    if not canonical_root.endswith(os.sep):
        root_prefix = canonical_root + os.sep
    else:
        root_prefix = canonical_root
    
    if resolved_target == canonical_root or not resolved_target.startswith(root_prefix):
        raise ValueError("Request disallowed: path escapes the approved root")
    
    # Step 5: Confirm the resolved target exists and is an ordinary file
    if not os.path.isfile(resolved_target):
        raise FileNotFoundError(f"Not an ordinary file: {resolved_target}")
    
    # Step 6: Open the validated path for reading and decode as UTF-8
    with open(resolved_target, 'r', encoding='utf-8') as f:
        return f.read()
