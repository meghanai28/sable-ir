import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    # Normalize reports_root to absolute path
    reports_root = os.path.abspath(reports_root)
    
    # Normalize the user-supplied filename
    normalized_filename = os.path.normpath(filename)
    
    # Split into components and discard empty ones
    parts = []
    for part in normalized_filename.split(os.sep):
        if part and part != '.':
            parts.append(part)
    
    # Check if filename is empty, resolves to '.', or fails to identify a specific file
    if not parts:
        raise ValueError("Filename must identify a specific file beneath the root")
    
    # Construct candidate target path
    target = os.path.normpath(os.path.join(reports_root, normalized_filename))
    
    # Verify strict containment: target must not be identical to reports_root
    if target == reports_root:
        raise ValueError("Target cannot be the root directory itself")
    
    # Verify target is strictly beneath reports_root
    if not target.startswith(reports_root + os.sep):
        raise ValueError("Target path escapes the approved root")
    
    # Component-by-component filesystem walk to enforce symlink prohibition
    current = reports_root
    for component in parts:
        current = os.path.join(current, component)
        if os.path.islink(current):
            raise ValueError("Symbolic links in user-selected path components are not allowed")
        # If component doesn't exist, stop checking deeper components
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
                # Translate symlink-related errors to ValueError
                if e.errno == getattr(os, 'ELOOP', 40) or e.errno == getattr(os, 'EMLINK', 31):
                    raise ValueError("Symbolic link detected during open")
                raise
            file_obj = os.fdopen(fd, 'r', encoding='utf-8')
        else:
            file_obj = open(current, 'r', encoding='utf-8')
            fd = file_obj.fileno()
        
        # Verify the opened file is a regular file
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise ValueError("Target is not a regular file")
        
        # Read and return contents
        contents = file_obj.read()
        return contents
    except ValueError:
        # Re-raise ValueError without modification
        raise
    except FileNotFoundError:
        # Allow FileNotFoundError to propagate untouched
        raise
    except OSError as e:
        # Translate O_NOFOLLOW symlink refusal to ValueError
        if hasattr(os, 'ELOOP') and e.errno == os.ELOOP:
            raise ValueError("Symbolic link detected during open")
        if hasattr(os, 'EMLINK') and e.errno == os.EMLINK:
            raise ValueError("Symbolic link detected during open")
        raise
    finally:
        if file_obj is not None:
            file_obj.close()
        elif fd is not None:
            os.close(fd)
