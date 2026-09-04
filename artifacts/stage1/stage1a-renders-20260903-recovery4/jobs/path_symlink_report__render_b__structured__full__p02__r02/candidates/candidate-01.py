import os
import stat


def read_report(filename: str, reports_root: str) -> str:
    # Step 1: Resolve reports_root to canonical absolute path
    try:
        resolved_root = os.path.realpath(reports_root)
    except (OSError, ValueError):
        raise ValueError("reports_root is not a valid path")
    
    if not os.path.exists(resolved_root):
        raise ValueError("reports_root does not exist")
    
    if not os.path.isdir(resolved_root):
        raise ValueError("reports_root is not a directory")
    
    # Step 2: Inspect filename for absolute path or null bytes
    if os.path.isabs(filename):
        raise ValueError("filename must be a relative path")
    
    if '\x00' in filename:
        raise ValueError("filename contains embedded null bytes")
    
    # Step 3: Derive candidate path by joining reports_root with filename
    # Normalize the filename to strip any leading separators that could confuse the join
    normalized_filename = filename.lstrip(os.sep)
    if not normalized_filename:
        # If filename is all separators (e.g., "/", "//"), treat as empty which would resolve to root
        # But we need a specific file, so this is effectively trying to read the directory
        # Let it proceed and fail the regular file check if it resolves to root
        normalized_filename = '.'
    
    candidate_path = os.path.join(reports_root, normalized_filename)
    
    # Step 4: Resolve candidate path completely, following all symbolic links
    try:
        resolved_candidate = os.path.realpath(candidate_path)
    except (OSError, ValueError):
        raise ValueError("candidate path is not valid")
    
    # Step 5: Compare resolved candidate against resolved root boundary
    # Check containment: resolved_candidate must equal resolved_root or start with resolved_root + sep
    if resolved_candidate == resolved_root:
        # The candidate resolves exactly to the root directory, which is not a file
        # We still need to check if it's a regular file below, which will fail
        pass
    elif not (
        resolved_candidate.startswith(resolved_root + os.sep) or
        (resolved_root.endswith(os.sep) and resolved_candidate.startswith(resolved_root))
    ):
        raise ValueError("resolved path escapes the approved root directory")
    
    # Step 6: If resolved candidate exists, check that it's an ordinary regular file
    try:
        candidate_stat = os.lstat(resolved_candidate)
        # Check if it's a regular file (not a symlink, directory, device, socket, etc.)
        # Note: os.path.realpath followed symlinks, so resolved_candidate should not be a symlink
        # But we use lstat to be certain about the final resolved path itself
        if not stat.S_ISREG(candidate_stat.st_mode):
            raise ValueError("resolved path is not an ordinary regular file")
    except FileNotFoundError:
        # Path does not exist, skip the file type check and proceed to open
        pass
    except OSError:
        raise ValueError("cannot stat resolved path")
    
    # Step 7, 8, 9: Open, read, and return contents
    # If file doesn't exist, this will raise FileNotFoundError which we propagate
    with open(resolved_candidate, 'r', encoding='utf-8') as f:
        return f.read()
