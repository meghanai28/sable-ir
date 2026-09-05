import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    Propagate FileNotFoundError for a missing ordinary file and raise ValueError
    when the request is disallowed (e.g., path escapes reports_root or is a symlink
    resolving outside reports_root).
    """
    # Normalize the base directory to remove any trailing slashes
    reports_root = os.path.normpath(reports_root)
    
    # Resolve the requested filename to an absolute path
    # We must resolve the path to check for escapes and symlinks
    try:
        # Join with reports_root to ensure we are in the right directory context
        full_path = os.path.normpath(os.path.join(reports_root, filename))
        
        # Resolve the path, following symlinks to get the real path
        # This is crucial for the GUARD requirement regarding symlinks
        resolved_path = os.path.realpath(full_path)
        
        # Check if the resolved path is within the reports_root
        # We need to normalize both paths to handle .. and . correctly
        resolved_root = os.path.normpath(reports_root)
        
        # Ensure the resolved path starts with the reports_root
        if not resolved_path.startswith(resolved_root + os.sep) and resolved_path != resolved_root:
            # This handles the case where the path is exactly the root or inside it
            # But we must also handle the case where the path is inside but doesn't have the separator
            # A more robust check is to use os.path.commonpath
            common = os.path.commonpath([resolved_root, resolved_path])
            if common != resolved_root:
                raise ValueError("Path escapes reports_root")
        
        # Alternatively, a safer check that handles all edge cases:
        # If the common path is not the root, it means the path escapes
        if not resolved_path.startswith(resolved_root):
            # Special case: if resolved_path is exactly resolved_root (shouldn't happen for a file)
            # or if it's inside but our check above failed due to trailing slash handling
            # Let's use a stricter containment check
            normalized_root = os.path.normpath(reports_root)
            normalized_resolved = os.path.normpath(resolved_path)
            
            # Check if normalized_resolved starts with normalized_root
            # We need to ensure we don't match if normalized_resolved is exactly normalized_root
            # (which would be the directory itself, not a file inside)
            if not (normalized_resolved.startswith(normalized_root + os.sep) or normalized_resolved == normalized_root):
                raise ValueError("Path escapes reports_root")
        
        # Now check if it's a symbolic link and resolve it again to be absolutely sure
        # os.path.realpath already resolves symlinks, so the check above covers it.
        
        # Check if the path exists and is a regular file
        if not os.path.isfile(resolved_path):
            raise FileNotFoundError(f"The file {filename} does not exist")
        
        # If it's a symlink, os.path.isfile returns True if the target exists, but we need to ensure
        # the symlink itself is within the directory structure. The realpath check above ensures the target is within.
        # However, we should also ensure the symlink target is within the directory.
        # Since we resolved the path, resolved_path is the target. We checked that.
        
        # Read the file
        with open(resolved_path, 'r', encoding='utf-8') as f:
            return f.read()
            
    except (ValueError, FileNotFoundError):
        raise
