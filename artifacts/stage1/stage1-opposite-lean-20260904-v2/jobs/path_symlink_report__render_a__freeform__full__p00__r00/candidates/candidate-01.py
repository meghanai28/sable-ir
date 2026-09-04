import os
import pathlib


def read_report(filename: str, reports_root: str) -> str:
    # Canonicalize reports_root to absolute path with all symlinks resolved
    canonical_root = os.path.realpath(os.path.abspath(reports_root))
    
    # Combine root with filename using OS path join semantics
    # Use os.path.join which handles absolute filename by replacing the left side
    combined_path = os.path.join(canonical_root, filename)
    
    # Resolve the combined path completely, following all symlinks recursively
    resolved_path = os.path.realpath(combined_path)
    
    # Ensure the resolved path is a proper descendant of canonical_root
    # Must be strictly beneath the root, not equal to it
    # Use path-boundary-aware comparison with os.path.commonpath or explicit prefix check
    try:
        # Use pathlib for robust comparison
        resolved = pathlib.Path(resolved_path)
        root = pathlib.Path(canonical_root)
        
        # Check if resolved path is relative to root and not equal to root
        try:
            relative = resolved.relative_to(root)
        except ValueError:
            # Not under root at all
            raise ValueError("Request disallowed: path escapes approved root")
        
        # Must be strictly beneath root, not equal to it
        # relative_to succeeds when equal, giving '.', so we check for that
        if relative == pathlib.Path('.'):
            raise ValueError("Request disallowed: path is the root itself")
        
        # Also verify using string-based prefix check to prevent partial matches
        # Ensure resolved_path starts with canonical_root followed by separator
        if not (resolved_path == canonical_root or 
                resolved_path.startswith(canonical_root + os.sep) or
                (os.altsep and resolved_path.startswith(canonical_root + os.altsep))):
            raise ValueError("Request disallowed: path escapes approved root")
            
    except ValueError as e:
        if "Request disallowed" in str(e):
            raise
        # Other ValueError from relative_to means not under root
        raise ValueError("Request disallowed: path escapes approved root")
    
    # Final verification: resolved path must not equal canonical_root
    if resolved_path == canonical_root:
        raise ValueError("Request disallowed: path is the root itself")
    
    # Verify it's strictly beneath with proper boundary check
    if not (
        resolved_path.startswith(canonical_root + os.sep) or
        (os.altsep and resolved_path.startswith(canonical_root + os.altsep))
    ):
        raise ValueError("Request disallowed: path escapes approved root")
    
    # Open as UTF-8 text file - FileNotFoundError propagates naturally
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
