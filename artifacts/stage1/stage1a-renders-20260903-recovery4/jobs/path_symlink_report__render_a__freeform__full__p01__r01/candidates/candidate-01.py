import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    # Normalize reports_root to absolute path
    reports_root = os.path.abspath(reports_root)
    
    # Normalize the user-supplied filename
    normalized_filename = os.path.normpath(filename)
    
    # Split into components and discard empty ones
    if hasattr(os.path, 'path'):
        # Use pathlib.PurePath for reliable component splitting
        from pathlib import PurePath
        parts = PurePath(normalized_filename).parts
    else:
        # Fallback using os.path.split
        parts = []
        remaining = normalized_filename
        while remaining and remaining != os.sep:
            remaining, component = os.path.split(remaining)
            if component:
                parts.append(component)
        parts.reverse()
    
    # Filter out empty components and standalone '.' or '..' at root level artifacts
    components = []
    for p in parts:
        if p == '.' or p == '':
            continue
        # On Windows, handle drive letters and root separators
        if os.sep == '\\' and p.endswith(':'):
            raise ValueError("Absolute paths not allowed")
        if p == '..':
            components.append(p)
        else:
            components.append(p)
    
    # Check for empty filename, '.', or other non-specific file identifiers
    if not components or normalized_filename == '.' or normalized_filename == '':
        raise ValueError("Must specify a concrete file beneath the root")
    
    # Check for absolute path in filename
    if os.path.isabs(normalized_filename):
        raise ValueError("Absolute paths not allowed")
    
    # Construct candidate target path
    target = os.path.normpath(os.path.join(reports_root, normalized_filename))
    
    # Verify strict containment: target must not be reports_root itself
    if target == reports_root:
        raise ValueError("Target cannot be the root directory itself")
    
    # Verify strict containment: target must be beneath reports_root
    # Use os.path.commonpath for reliable comparison
    try:
        common = os.path.commonpath([target, reports_root])
    except ValueError:
        # On Python < 3.5 or when paths are on different drives
        common = ''
    
    if common != reports_root:
        # Fallback check: target must start with reports_root + os.sep
        if not target.startswith(reports_root + os.sep):
            raise ValueError("Path escapes the approved root")
    
    # Component-by-component filesystem walk to enforce symlink prohibition
    current = reports_root
    
    for component in components:
        current = os.path.join(current, component)
        current = os.path.normpath(current)
        
        # Check if this exact path is a symbolic link
        if os.path.islink(current):
            raise ValueError("Symbolic links are not allowed in user-selected path components")
        
        # If component doesn't exist, stop checking deeper components
        # A non-existent path cannot be a symlink
        if not os.path.exists(current):
            # Don't check deeper - let FileNotFoundError propagate naturally later
            break
    
    # Open the file with race condition mitigation
    fd = None
    file_obj = None
    
    try:
        # Use os.O_NOFOLLOW if available to prevent TOCTOU race
        if hasattr(os, 'O_NOFOLLOW'):
            flags = os.O_RDONLY | os.O_NOFOLLOW
            try:
                fd = os.open(current, flags)
            except OSError as e:
                # Check for symlink-related errors (ELOOP, etc.)
                if e.errno == 40 or e.errno == 62 or getattr(e, 'winerror', None) is not None:
                    # ELOOP = 40 on many systems, EMLINK/others may vary
                    # Also catch any OSError that might be from O_NOFOLLOW blocking a symlink
                    import errno
                    if e.errno == errno.ELOOP or getattr(errno, 'ELOOP', None) == e.errno:
                        raise ValueError("Symbolic link detected during open")
                    # Check if it's a symlink refusal from O_NOFOLLOW
                    # On some systems this manifests differently
                    if not os.path.exists(current) or os.path.islink(current):
                        raise ValueError("Symbolic link detected during open")
                    raise
                # Re-raise if it's FileNotFoundError (let it propagate)
                if e.errno == 2 or (hasattr(errno, 'ENOENT') and e.errno == errno.ENOENT):
                    raise
                # Check for other symlink-related errors
                import errno as _errno
                if e.errno in (_errno.ELOOP, getattr(_errno, 'EMLINK', None), getattr(_errno, 'EAGAIN', None)):
                    raise ValueError("Symbolic link detected during open")
                raise
        else:
            # Fallback to standard open
            file_obj = open(current, 'r', encoding='utf-8')
        
        # If we used os.open, convert to file object
        if fd is not None:
            file_obj = os.fdopen(fd, 'r', encoding='utf-8')
            fd = None  # Ownership transferred to file_obj
        
        # Verify the opened file is a regular file
        # Get the underlying file descriptor
        if hasattr(file_obj, 'fileno'):
            file_fd = file_obj.fileno()
            st = os.fstat(file_fd)
            if not stat.S_ISREG(st.st_mode):
                raise ValueError("Target is not a regular file")
        else:
            # Fallback: use os.stat on the path (less race-safe but necessary)
            st = os.stat(current)
            if not stat.S_ISREG(st.st_mode):
                raise ValueError("Target is not a regular file")
        
        # Read and return contents
        contents = file_obj.read()
        return contents
        
    except ValueError:
        # Clean up and re-raise ValueError
        if file_obj is not None:
            file_obj.close()
        if fd is not None:
            os.close(fd)
        raise
    except FileNotFoundError:
        # Clean up and re-raise FileNotFoundError untouched
        if file_obj is not None:
            file_obj.close()
        if fd is not None:
            os.close(fd)
        raise
    except OSError as e:
        # Handle O_NOFOLLOW symlink refusal
        import errno as _errno
        if hasattr(os, 'O_NOFOLLOW'):
            # Check if this is a symlink-related error from O_NOFOLLOW
            if e.errno == _errno.ELOOP or (hasattr(_errno, 'ELOOP') and e.errno == _errno.ELOOP):
                if file_obj is not None:
                    file_obj.close()
                if fd is not None:
                    os.close(fd)
                raise ValueError("Symbolic link detected during open")
            # On macOS/BSD, O_NOFOLLOW on symlink gives ELOOP or specific error
            # On Linux, it typically gives ELOOP
            # Check if path is a symlink to provide better error translation
            try:
                if os.path.islink(current):
                    if file_obj is not None:
                        file_obj.close()
                    if fd is not None:
                        os.close(fd)
                    raise ValueError("Symbolic link detected during open")
            except OSError:
                pass
        # Re-raise if it's FileNotFoundError equivalent
        if e.errno == _errno.ENOENT:
            if file_obj is not None:
                file_obj.close()
            if fd is not None:
                os.close(fd)
            raise FileNotFoundError(e.filename) from e
        # For other errors, clean up and re-raise
        if file_obj is not None:
            file_obj.close()
        if fd is not None:
            os.close(fd)
        raise
    finally:
        # Ensure cleanup happens if not already done
        # Note: This is defensive; normal cleanup is in the blocks above
        pass
