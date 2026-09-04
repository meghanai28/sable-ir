import os
import stat


def read_report(filename: str, reports_root: str) -> str:
    # Normalize reports_root to absolute path
    root = os.path.abspath(reports_root)
    
    # Normalize the user-supplied filename
    normalized_filename = os.path.normpath(filename)
    
    # Split into components and discard empty ones
    parts = []
    for part in normalized_filename.split(os.sep):
        if part:
            parts.append(part)
    
    # Check for empty filename, '.', or other non-specific paths
    if not parts:
        raise ValueError("filename must identify a specific file beneath the root")
    
    # Construct candidate target path
    target = os.path.normpath(os.path.join(root, normalized_filename))
    
    # Verify strict containment: target must not be root, and must be beneath root
    if target == root:
        raise ValueError("target path cannot be the root directory itself")
    
    # Ensure target is strictly beneath root
    if not (target.startswith(root + os.sep)):
        raise ValueError("target path escapes the approved root")
    
    # Verify with commonpath as additional safety check
    try:
        common = os.path.commonpath([target, root])
    except ValueError:
        raise ValueError("target path escapes the approved root")
    if common != root:
        raise ValueError("target path escapes the approved root")
    
    # Component-by-component walk to enforce symlink prohibition
    current = root
    for component in parts:
        current = os.path.join(current, component)
        # Check if this exact path is a symbolic link
        if os.path.islink(current):
            raise ValueError("symbolic link detected in user-selected path component")
        # If component doesn't exist, stop checking deeper components
        # FileNotFoundError will be raised naturally by subsequent operations
        if not os.path.exists(current):
            break
    
    # Open the file with O_NOFOLLOW if available to mitigate TOCTOU
    fd = None
    file_obj = None
    try:
        if hasattr(os, 'O_NOFOLLOW'):
            try:
                fd = os.open(current, os.O_RDONLY | os.O_NOFOLLOW)
            except OSError as e:
                # Check if this is a symlink-related error (ELOOP, etc.)
                # ELOOP is typically errno 40 on many systems, but we check the message too
                import errno
                if e.errno == errno.ELOOP or 'too many levels' in str(e).lower() or 'symbolic link' in str(e).lower():
                    raise ValueError("symbolic link detected")
                # Re-raise other errors, including FileNotFoundError
                raise
            file_obj = os.fdopen(fd, 'r', encoding='utf-8')
            # fdopen succeeded, fd is now managed by file_obj
            fd = None
        else:
            file_obj = open(current, 'r', encoding='utf-8')
        
        # Verify the opened file is a regular file
        st = os.fstat(file_obj.fileno())
        if not stat.S_ISREG(st.st_mode):
            raise ValueError("target is not a regular file")
        
        # Read and return contents
        contents = file_obj.read()
        return contents
        
    finally:
        if file_obj is not None:
            file_obj.close()
        elif fd is not None:
            os.close(fd)
