import os

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    Propagates FileNotFoundError for a missing ordinary file and raises ValueError
    when the request is disallowed (e.g., path escapes root or is absolute).
    """
    # Resolve the reports_root to an absolute path if it isn't already
    try:
        root_dir = os.path.abspath(reports_root)
    except (ValueError, TypeError):
        raise ValueError("Invalid reports_root")

    # Normalize the filename to remove redundant separators and resolve ..
    # We do not resolve symlinks yet, just normalize the path string
    normalized_filename = os.path.normpath(filename)

    # Check if the filename is absolute; if so, reject it immediately
    if os.path.isabs(normalized_filename):
        raise ValueError("Absolute paths are not allowed")

    # Construct the candidate path by joining root_dir and normalized_filename
    # This ensures the path is relative to the root before further checks
    candidate_path = os.path.join(root_dir, normalized_filename)

    # Normalize the candidate path to handle any remaining .. or . segments
    # This must be done before checking containment
    resolved_candidate = os.path.normpath(candidate_path)

    # Check if the resolved candidate escapes the root directory
    # We compare the resolved path against the root directory
    if not resolved_candidate.startswith(root_dir + os.sep) and resolved_candidate != root_dir:
        raise ValueError("Path escapes the reports_root directory")

    # Now resolve the full path, following symbolic links
    # This is the dangerous operation that must be validated after containment check
    try:
        final_target = os.path.realpath(resolved_candidate)
    except (OSError, ValueError):
        raise ValueError("Invalid path")

    # Re-check containment after resolving symlinks
    # The resolved target must still be inside the reports_root
    if not final_target.startswith(root_dir + os.sep) and final_target != root_dir:
        raise ValueError("Resolved path escapes the reports_root directory")

    # Verify it is an existing file (not a directory)
    if not os.path.isfile(final_target):
        raise FileNotFoundError(f"The file {filename} does not exist")

    # Read the file as UTF-8
    try:
        with open(final_target, 'r', encoding='utf-8') as f:
            return f.read()
    except (IOError, OSError):
        raise FileNotFoundError(f"Cannot read the file {filename}")
