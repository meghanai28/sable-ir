import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    Propagate FileNotFoundError for a missing ordinary file and raise ValueError when the request is disallowed.
    """
    # Normalize the root to an absolute path to ensure consistent handling
    resolved_root = os.path.normpath(os.path.abspath(reports_root))
    
    # Resolve the requested filename to an absolute path
    requested_path = os.path.normpath(os.path.abspath(filename))
    
    # Guard: Reject absolute filenames that do not start with the root
    if not requested_path.startswith(resolved_root + os.sep) and requested_path != resolved_root:
        raise ValueError("Request escapes reports_root")
    
    # Guard: Normalize the path and check for escapes (e.g., ..)
    # After abspath and normpath, if the path still doesn't start with the root (excluding the root itself), it's invalid
    if not requested_path.startswith(resolved_root + os.sep) and requested_path != resolved_root:
        raise ValueError("Request escapes reports_root")
    
    # Guard: Walk each user-selected path component and check for symbolic links
    # We need to resolve the path step-by-step to catch symlinks in any component
    current_path = resolved_root
    
    # Split the filename into components, handling the root separately
    # If filename is just a name, we start from root + name
    # If filename contains .. or is absolute, we validate the path construction
    
    # Construct the full path relative to root
    if filename.startswith(os.sep):
        raise ValueError("Absolute filenames are not allowed")
    
    # Ensure the path is within root by resolving it
    full_path = os.path.join(resolved_root, filename)
    resolved_full_path = os.path.normpath(os.path.abspath(full_path))
    
    # Final containment check
    if not resolved_full_path.startswith(resolved_root + os.sep) and resolved_full_path != resolved_root:
        raise ValueError("Request escapes reports_root")
    
    # Guard: Check for symbolic links in any component of the path
    # We walk up the path components from the root to the target
    parts = os.path.normpath(os.path.abspath(filename)).replace(resolved_root, '').split(os.sep) if filename else []
    
    # Reconstruct path components to check
    current_check = resolved_root
    if filename:
        # Split filename by path separators
        components = []
        if filename.startswith(os.sep):
            raise ValueError("Absolute filenames are not allowed")
        
        # Handle the first component
        if not filename:
            components = []
        else:
            # Split by path separator, handling the root
            temp_parts = filename.split(os.sep)
            # The first part is the name, subsequent are directories if any
            # Actually, we should just walk the path from root to the file
            pass
        
        # Simpler approach: walk the path string
        current_check = resolved_root
        if filename:
            # Split the filename into components
            # We need to check each segment
            segments = []
            if not filename:
                pass
            else:
                # If filename is just a name, it's one segment
                # If it has separators, split them
                temp = filename
                if temp.startswith(os.sep):
                    raise ValueError("Absolute filenames are not allowed")
                
                # Split by separator
                if os.sep in filename:
                    segments = filename.split(os.sep)
                else:
                    segments = [filename]
            
            # Walk through segments
            for i, segment in enumerate(segments):
                # Check if the segment itself is a symlink
                if segment:
                    # Construct the path to check
                    check_path = current_check
                    if segment:
                        check_path = os.path.join(check_path, segment)
                    else:
                        check_path = current_check
                    
                    # Resolve the path to check for symlinks
                    resolved_check = os.path.normpath(os.path.abspath(check_path))
                    
                    # Check if any part of the path is a symlink
                    # We need to check the directory leading up to the segment too
                    # But the requirement says "walk each user-selected path component"
                    # So we check the segment and its parent directories if they are part of the path construction
                    
                    # Check if the resolved path is a symlink
                    if os.path.islink(resolved_check):
                        raise ValueError("Symbolic link found in path")
                    
                    # Also check if the parent directory is a symlink (for intermediate components)
                    # But the requirement focuses on the user-selected components
                    # Let's check the directory if it exists and is a symlink
                    if os.path.isdir(current_check):
                        if os.path.islink(current_check):
                            raise ValueError("Symbolic link found in path")
                    
                    current_check = resolved_check
    
    # Check if the final file is a symlink
    if os.path.islink(resolved_full_path):
        raise ValueError("Symbolic link found in path")
    
    # Check if the file exists and is an ordinary file
    if not os.path.isfile(resolved_full_path):
        raise FileNotFoundError(f"File not found: {resolved_full_path}")
    
    # Read the file as UTF-8
    with open(resolved_full_path, 'r', encoding='utf-8') as f:
        return f.read()
