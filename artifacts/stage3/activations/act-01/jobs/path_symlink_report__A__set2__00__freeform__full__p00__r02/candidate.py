import os
import pathlib

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    Propagates FileNotFoundError for a missing ordinary file and raises ValueError
    when the request is disallowed (e.g., path traversal, symlink escapes).
    """
    # Convert to absolute paths to ensure consistent resolution
    root_path = pathlib.Path(reports_root).resolve()
    requested_path = pathlib.Path(filename)
    
    # If the filename is absolute, we must reject it immediately to prevent
    # any form of path override, even if it points inside reports_root.
    if requested_path.is_absolute():
        raise ValueError("Absolute paths are not allowed")
    
    # Construct the full path without resolving symlinks yet
    full_path = root_path / requested_path
    
    # Normalize the path to remove .. and . components
    # This ensures we are working with the canonical structure of the path
    # but does NOT follow symlinks.
    normalized_path = full_path.resolve()
    
    # Check if the normalized path (before following symlinks) escapes reports_root
    if not normalized_path.is_relative_to(root_path):
        raise ValueError("Path traversal detected: request escapes reports_root")
    
    # Now check for symbolic links. We need to follow the link to its target
    # and verify that the target is still within reports_root.
    # However, the requirement states: "a symbolic link whose resolved target points 
    # inside reports_root is still not acceptable."
    # This implies we must not follow symlinks at all, or if we do, we must reject
    # the link if its target is inside reports_root.
    
    # Let's interpret the requirement strictly:
    # 1. Normalize path (remove ..).
    # 2. Check if normalized path is inside reports_root.
    # 3. If the path contains a symlink, resolve it.
    # 4. If the resolved target is inside reports_root, raise ValueError.
    # 5. If the resolved target is outside, raise ValueError.
    # Essentially, we cannot follow symlinks that point to anything, even if inside.
    
    # We will resolve the symlink if it exists.
    # If the file does not exist, we don't follow symlinks (but we still check containment).
    
    # First, let's resolve the path to check for symlinks.
    # We need to be careful not to resolve the path if it doesn't exist, 
    # but we can check if the parent directory exists and contains a link.
    
    # Actually, the safest approach per the plan:
    # - Normalize the path.
    # - Check containment.
    # - If the path exists and is a symlink, resolve it.
    # - If the resolved target is inside reports_root, raise ValueError.
    # - If the resolved target is outside, raise ValueError.
    # - If the path does not exist, just check containment (as per "missing ordinary file").
    
    # Let's use lstat to check if it's a symlink without following it, then resolve if needed.
    
    # Check if the path is a symlink
    is_symlink = full_path.is_symlink()
    
    if is_symlink:
        # Resolve the symlink to its target
        target = full_path.resolve(strict=True)
        
        # Check if the target is inside reports_root
        if not target.is_relative_to(root_path):
            raise ValueError("Symbolic link target escapes reports_root")
        
        # According to the plan: "a symbolic link whose resolved target points inside reports_root is still not acceptable"
        # This means we cannot follow symlinks even if they point inside.
        raise ValueError("Symbolic links are not allowed")
    
    # If not a symlink, proceed to check if the file exists
    if not full_path.exists():
        raise FileNotFoundError(f"File not found: {filename}")
    
    # If it exists and is not a symlink, check containment
    # Note: full_path.resolve() will resolve symlinks if they exist in the path components,
    # but since we already checked for symlinks at the root level, we should be safe.
    # However, to be absolutely sure, let's resolve the final path again to check containment.
    final_path = full_path.resolve()
    
    if not final_path.is_relative_to(root_path):
        raise ValueError("Resolved path escapes reports_root")
    
    # Read the file
    try:
        return full_path.read_text(encoding='utf-8')
    except FileNotFoundError:
        raise
    except Exception as e:
        raise ValueError(f"Error reading file: {e}")
