import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    Propagates FileNotFoundError for a missing ordinary file and raises ValueError
    when the request is disallowed (path escapes root or is a symlink pointing outside).
    """
    # Normalize the root directory to an absolute path
    resolved_root = os.path.normpath(os.path.abspath(reports_root))
    
    # Resolve the requested filename to an absolute path
    # We need to handle the case where filename is relative or absolute
    requested_path = os.path.abspath(filename)
    
    # Ensure the requested path is under the root (basic containment check)
    # We use os.path.commonpath to verify containment, but for robustness
    # we check that the resolved path starts with the root + separator or is the root itself
    try:
        common = os.path.commonpath([resolved_root, requested_path])
        if common != resolved_root:
            raise ValueError(f"Path '{filename}' is not within the reports root '{reports_root}'")
    except ValueError:
        # This can happen if paths are on different drives (Windows) or invalid
        raise ValueError(f"Invalid path structure for '{filename}'")
    
    # Get the directory of the root and ensure we are working with the same drive/separator
    # Now, resolve the target path, following symbolic links to check the final destination
    # We must check the symlink target's resolution against the root
    
    # Check if the file exists and is a regular file before following symlinks for the read
    # However, the plan says: resolve and check containment before opening, and follow symlinks for the check.
    # We need to resolve the path to its final target to ensure it doesn't escape via a symlink.
    
    # First, check if the initial path (or its resolved components) escapes the root
    # We normalize the requested path
    norm_filename = os.path.normpath(filename)
    
    # If the filename is absolute, we already checked containment above via commonpath
    # If relative, it's relative to current dir, but the plan says "joined beneath reports_root"
    # The plan says: "SOURCE: filename supplied by the caller, joined beneath reports_root"
    # This implies the path to read is: os.path.join(reports_root, filename)
    
    target_path = os.path.join(reports_root, filename)
    
    # Normalize the target path
    target_path = os.path.normpath(target_path)
    
    # Verify containment of the normalized path relative to root
    if not target_path.startswith(resolved_root + os.sep) and target_path != resolved_root:
        raise ValueError(f"Path '{filename}' escapes the reports root '{reports_root}'")
    
    # Now resolve the full path, following symbolic links, to check the final destination
    # os.path.realpath resolves symlinks and returns the absolute path
    final_target = os.path.realpath(target_path)
    
    # Check if the final resolved target is still within the root
    # We need to handle the case where the symlink points outside the root
    if not final_target.startswith(resolved_root + os.sep) and final_target != resolved_root:
        raise ValueError(f"Symbolic link or path resolves outside the reports root '{reports_root}'")
    
    # Check if the final target is a regular file
    try:
        file_stat = os.stat(final_target)
        if not stat.S_ISREG(file_stat.st_mode):
            raise ValueError(f"Target '{filename}' is not a regular file")
    except FileNotFoundError:
        raise FileNotFoundError(f"File '{filename}' not found")
    
    # Read the file
    with open(final_target, 'r', encoding='utf-8') as f:
        return f.read()
