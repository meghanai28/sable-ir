import os
import pathlib
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
    # Use pathlib to handle joining properly, ensuring filename is treated as relative
    candidate = os.path.join(resolved_root, filename.lstrip(os.sep))
    
    # Step 4: Resolve candidate path completely, following all symlinks
    try:
        resolved_candidate = os.path.realpath(candidate)
    except (OSError, ValueError):
        raise ValueError("candidate path could not be resolved")
    
    # Step 5: Compare resolved candidate against resolved root boundary
    # Ensure candidate is contained within root
    if resolved_candidate == resolved_root:
        # The candidate resolves to the root directory itself, which is not a file
        # This will fail the file check later, but we still need to check containment
        pass
    elif not (
        resolved_candidate.startswith(resolved_root + os.sep) or
        (os.altsep is not None and resolved_candidate.startswith(resolved_root + os.altsep))
    ):
        raise ValueError("resolved path escapes the approved root directory")
    
    # Step 6: Check file type if resolved path exists
    if os.path.lexists(resolved_candidate):
        # Use lstat after realpath since realpath follows all symlinks
        # os.path.realpath followed by os.path.exists/stat follows symlinks
        try:
            file_stat = os.stat(resolved_candidate)
        except OSError:
            # If we can't stat it, it might be a dangling symlink or other issue
            # Let the open call handle it
            pass
        else:
            if not stat.S_ISREG(file_stat.st_mode):
                raise ValueError("resolved path is not an ordinary regular file")
    
    # Steps 7-9: Open, read, and return file contents
    with open(resolved_candidate, 'r', encoding='utf-8') as f:
        return f.read()
