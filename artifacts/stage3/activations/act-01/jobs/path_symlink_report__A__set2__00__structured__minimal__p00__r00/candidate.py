import os
import sys

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    Propagate FileNotFoundError for a missing ordinary file and raise ValueError
    when the request is disallowed (path escapes reports_root or follows symlinks
    outside reports_root).
    """
    # Normalize the base directory to remove trailing slashes and resolve any
    # immediate parent references if possible, but keep it as a string for
    # comparison. We will resolve it fully to handle symlinks in the root itself
    # if necessary, though typically root is a directory.
    # We resolve reports_root to its absolute path to handle relative paths
    # and symlinks in the root directory name.
    resolved_root = os.path.realpath(reports_root)
    
    # Construct the full path by joining the root with the filename
    # This handles cases where filename is absolute (though we want to prevent that)
    # and relative.
    full_path = os.path.join(resolved_root, filename)
    
    # Resolve the full path to check for escapes and symlinks
    resolved_path = os.path.realpath(full_path)
    
    # Ensure the resolved path is within the resolved root
    # We use os.path.commonpath to ensure the path is a subdirectory of the root
    # or equal to the root.
    try:
        common = os.path.commonpath([resolved_root, resolved_path])
    except ValueError:
        # This can happen if paths are on different drives (Windows) or otherwise incompatible
        raise ValueError("Path escapes reports_root")
    
    if common != resolved_root:
        raise ValueError("Path escapes reports_root")
    
    # Check if the file exists and is a regular file
    if not os.path.isfile(full_path):
        # os.path.isfile follows symlinks, but we already checked the resolved path.
        # If the original path is a symlink to a file outside, os.path.isfile might return True
        # for the resolved path, but we caught that.
        # If the original path is a directory or doesn't exist, we raise FileNotFoundError.
        # Note: os.path.isfile(full_path) returns False if full_path is a broken symlink or a directory.
        # However, if full_path is a symlink to a file, os.path.isfile returns True.
        # We need to ensure we are not following a symlink that was created *after* resolution
        # but before this check. Actually, os.path.realpath(full_path) resolves the symlink.
        # If the symlink target is outside, we caught it.
        # If the symlink target is inside, we are good.
        # If the target doesn't exist, os.path.isfile(full_path) is False.
        # So checking os.path.isfile(full_path) is sufficient for "missing ordinary file".
        raise FileNotFoundError(f"File not found: {filename}")
    
    # Read the file content as UTF-8
    with open(full_path, 'r', encoding='utf-8') as f:
        return f.read()
