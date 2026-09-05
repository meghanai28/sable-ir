import os
import sys

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    Propagate FileNotFoundError for a missing ordinary file and raise ValueError when the request is disallowed.
    """
    # Resolve the reports_root to an absolute path if necessary
    resolved_root = os.path.abspath(reports_root)
    
    # Construct the target path by joining filename with reports_root
    # We must ensure we don't accidentally use the filename as an absolute path to escape
    target_path = os.path.normpath(os.path.join(reports_root, filename))
    
    # Normalize the target path to remove any .. or . components that might be in the input
    normalized_target = os.path.normpath(target_path)
    
    # Resolve the full path, following symbolic links
    # If the file doesn't exist, os.path.realpath will still resolve the link if it exists,
    # but we need to check if it's a symlink first or handle missing files.
    # However, the plan says: "resolve the complete target path, following symbolic links, and raise ValueError unless the fully resolved target remains inside reports_root"
    # This implies we resolve the symlink target.
    
    try:
        # Check if the path exists (as a file or directory)
        # If it doesn't exist, we can't resolve the symlink target yet, but we can check containment of the normalized path
        # However, the plan says "resolve... and raise ValueError unless...".
        # If the file is missing, we propagate FileNotFoundError.
        # If the file exists, we resolve it.
        
        # First, check if the normalized path is within the root before resolving symlinks to prevent path traversal via .. in the input
        if not normalized_target.startswith(resolved_root + os.sep) and normalized_target != resolved_root:
            raise ValueError("Request is disallowed: path escapes reports_root")
        
        # If the file exists, resolve it to follow symlinks
        if os.path.isfile(normalized_target):
            resolved_target = os.path.realpath(normalized_target)
            # Re-check containment after resolving symlinks
            if not resolved_target.startswith(resolved_root + os.sep) and resolved_target != resolved_root:
                raise ValueError("Request is disallowed: resolved symlink escapes reports_root")
        else:
            # If it's not a file (e.g., directory or doesn't exist), we still need to check containment of the normalized path
            # But the plan says "raise ValueError unless the fully resolved target remains inside reports_root".
            # If it doesn't exist, there is no "fully resolved target" in the sense of a file.
            # The plan says "Propagate FileNotFoundError for a missing ordinary file".
            # So if it's not an ordinary file (e.g., directory) or missing, we should handle it.
            # "missing ordinary file" -> FileNotFoundError.
            # "request is disallowed" -> ValueError.
            # If the path is a directory, it's not an ordinary file, so we should probably raise ValueError or treat it as disallowed?
            # The plan says "raise ValueError when the request is disallowed". A directory is not a report file.
            # Let's assume only ordinary files are allowed.
            raise ValueError("Request is disallowed: path is not an ordinary file")
            
    except (ValueError, TypeError):
        raise
    
    # Now, open and read the file
    if not os.path.isfile(normalized_target):
        raise FileNotFoundError(f"File not found: {filename}")
    
    # Read the file
    with open(normalized_target, 'r', encoding='utf-8') as f:
        return f.read()
