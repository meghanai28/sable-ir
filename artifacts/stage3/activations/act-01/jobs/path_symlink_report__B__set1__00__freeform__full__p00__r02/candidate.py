import os

def read_report(filename: str, reports_root: str) -> str:
    # Normalize the base root path to an absolute path to prevent path traversal via relative components
    resolved_root = os.path.normpath(os.path.abspath(reports_root))
    
    # Construct the candidate path by joining the root and the filename
    candidate_path = os.path.normpath(os.path.join(resolved_root, filename))
    
    # Check if the candidate path escapes the reports_root directory
    # This check must happen before resolving symlinks to prevent traversal via symlink name
    if not candidate_path.startswith(resolved_root + os.sep) and candidate_path != resolved_root:
        raise ValueError("Path escapes reports_root")
    
    # Resolve the target path, following symbolic links
    resolved_target = os.path.realpath(candidate_path)
    
    # Ensure the resolved target is still within the reports_root directory
    # This prevents a symlink that points outside the root from being accessed
    if not resolved_target.startswith(resolved_root + os.sep) and resolved_target != resolved_root:
        raise ValueError("Resolved path escapes reports_root")
    
    # Verify the resolved path is a regular file
    if not os.path.isfile(resolved_target):
        raise FileNotFoundError(f"The file {filename} does not exist or is not a regular file")
    
    # Read and return the UTF-8 content
    with open(resolved_target, 'r', encoding='utf-8') as f:
        return f.read()
