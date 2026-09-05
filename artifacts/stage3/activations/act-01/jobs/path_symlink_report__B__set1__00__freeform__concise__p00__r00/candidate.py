import os

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    Propagates FileNotFoundError for a missing ordinary file and raises ValueError
    when the request is disallowed (path escapes root or is a symlink outside root).
    """
    # Normalize the base directory to remove any trailing slashes and ensure it's absolute
    # if not already. We will resolve it to an absolute path for comparison.
    resolved_root = os.path.realpath(reports_root)
    
    # Construct the target path by joining reports_root and filename
    # We use os.path.join, but since filename can be absolute, we need to be careful.
    # The plan says "joined beneath reports_root", implying reports_root is the prefix.
    # If filename is absolute, it likely escapes the root, but we must check.
    target_path = os.path.join(resports_root, filename)
    
    # Resolve the path to an absolute path, resolving .. segments but not symlinks yet
    # Actually, os.path.realpath does resolve symlinks. We need to do two steps:
    # 1. Normalize (resolve .. and absolute) without following symlinks.
    # 2. Check containment.
    # 3. Resolve symlinks.
    # 4. Check containment again.
    
    # Step 1: Normalize the requested path (resolve .., make absolute)
    # If filename is absolute, the result is the filename itself.
    # The requirement says "joined beneath reports_root", so if filename is absolute,
    # it should probably be rejected or treated as absolute.
    # Standard behavior for "joined beneath": if filename is absolute, it replaces the prefix.
    # However, the security constraint says "may be absolute". If it's absolute,
    # it definitely escapes reports_root unless it's inside.
    
    # Let's use os.path.realpath on the joined path first to see the final location,
    # but we need to check the *normalized* path before resolving symlinks to ensure
    # the user didn't try to escape via .. in the name itself.
    
    # Actually, the safest way is:
    # 1. Compute the candidate path = os.path.normpath(os.path.join(reports_root, filename))
    #    This handles .. and absolute paths. If filename is absolute, normpath makes it absolute.
    #    If it's absolute, it will likely be outside reports_root.
    # 2. Check if candidate_path starts with reports_root (with separator) or equals reports_root.
    #    Wait, os.path.normpath might resolve .. in the filename part.
    #    Example: reports_root="/app", filename="../etc/passwd" -> normpath -> "/etc/passwd".
    #    We must ensure the resolved path (without symlink following) is inside reports_root.
    
    # Let's use os.path.realpath on the joined path to get the final location.
    # But we must validate the *intended* path before following symlinks.
    
    # Re-read plan: "Normalize the requested path and raise ValueError if it escapes the resolved reports_root"
    # "Normalize" usually means resolving .. and making absolute.
    # "Resolve the complete target path, following symbolic links"
    # "raise ValueError unless the fully resolved target remains inside reports_root"
    
    # So:
    # 1. Join reports_root and filename.
    # 2. Normalize (resolve .., make absolute) -> this is the "normalized requested path".
    # 3. Check if this normalized path is inside reports_root. If not, raise ValueError.
    # 4. Resolve symlinks -> final target.
    # 5. Check if final target is inside reports_root. If not, raise ValueError.
    # 6. Open and read.
    
    # Note: os.path.normpath does not resolve symlinks. os.path.realpath does.
    # We need to check containment before resolving symlinks (step 3).
    
    # Construct the path
    candidate_path = os.path.join(reports_root, filename)
    
    # Normalize: resolve .. and ensure absolute
    # If filename is absolute, os.path.join might just return filename.
    # We need to ensure the path is absolute and normalized.
    normalized_path = os.path.normpath(candidate_path)
    
    # Check containment of normalized_path relative to resolved_root
    # We need to handle the case where normalized_path is equal to resolved_root or starts with it.
    # Since resolved_root is already real (absolute), we can check if normalized_path starts with resolved_root + os.sep
    # or if normalized_path == resolved_root.
    
    # However, normalized_path might be just the filename if filename was absolute.
    # If filename was absolute, normalized_path is absolute.
    # If it's not inside reports_root, it's bad.
    
    # Let's ensure reports_root is absolute and normalized.
    if not os.path.isabs(reports_root):
        reports_root = os.path.abspath(reports_root)
    reports_root = os.path.normpath(reports_root)
    
    # Check if normalized_path is within reports_root
    # We can use os.path.commonpath or simple string prefix check with separator.
    # Common approach: commonpath([root, path]) == root
    try:
        common = os.path.commonpath([reports_root, normalized_path])
        if common != reports_root:
            raise ValueError("Path escapes reports_root before resolving symlinks")
    except ValueError:
        # This happens if paths are on different drives (Windows) or invalid
        raise ValueError("Path escapes reports_root")
    
    # Now resolve symlinks
    resolved_target = os.path.realpath(normalized_path)
    
    # Check containment of resolved_target
    try:
        common = os.path.commonpath([reports_root, resolved_target])
        if common != reports_root:
            raise ValueError("Symbolic link escapes reports_root")
    except ValueError:
        raise ValueError("Symbolic link escapes reports_root")
    
    # Check if it's a file and ordinary (not directory)
    if not os.path.isfile(resolved_target):
        raise FileNotFoundError(f"File not found: {resolved_target}")
    
    # Read the file
    with open(resolved_target, 'r', encoding='utf-8') as f:
        return f.read()
