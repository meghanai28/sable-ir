import os
import stat


def read_report(filename: str, reports_root: str) -> str:
    # Normalize the reports_root to an absolute path
    reports_root = os.path.abspath(reports_root)

    # Normalize the user-supplied filename
    normalized_filename = os.path.normpath(filename)

    # Split into components and discard empty ones
    if isinstance(normalized_filename, str):
        parts = []
        temp = normalized_filename
        while True:
            temp, component = os.path.split(temp)
            if component:
                parts.append(component)
            elif temp:
                parts.append(temp)
                break
            else:
                break
        parts.reverse()
    else:
        parts = list(normalized_filename)

    # Filter out empty components
    components = [p for p in parts if p and p != '.']

    # Check if filename is empty, resolves to '.', or fails to identify a specific file
    if not normalized_filename or normalized_filename == '.' or not components:
        raise ValueError("Must specify a concrete file beneath the root")

    # Construct candidate target path
    target = os.path.normpath(os.path.join(reports_root, normalized_filename))

    # Verify strict containment: target must not be identical to reports_root
    if target == reports_root:
        raise ValueError("Target cannot be the root directory itself")

    # Verify target is strictly beneath reports_root
    try:
        common = os.path.commonpath([target, reports_root])
    except ValueError:
        raise ValueError("Target escapes the approved root")

    if common != reports_root:
        raise ValueError("Target escapes the approved root")

    # Alternative check: ensure target starts with reports_root + os.sep
    if not target.startswith(reports_root + os.sep):
        raise ValueError("Target escapes the approved root")

    # Component-by-component filesystem walk to enforce symlink prohibition
    current = reports_root
    for component in components:
        current = os.path.join(current, component)
        # Check if this exact path is a symbolic link
        if os.path.islink(current):
            raise ValueError("Symbolic link detected in user-selected path component")
        # If component does not exist, stop checking deeper components
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
                if e.errno == getattr(__import__('errno'), 'ELOOP', None) or \
                   e.errno == getattr(__import__('errno'), 'EMLINK', None) or \
                   e.errno == getattr(__import__('errno'), 'EACCES', None) or \
                   'link' in str(e).lower():
                    # Check if it's specifically a symlink issue
                    import errno
                    if e.errno == errno.ELOOP:
                        raise ValueError("Symbolic link detected")
                    # For other cases, re-raise to let other handlers deal with it
                    # But we need to be careful about FileNotFoundError
                    if e.errno == errno.ENOENT:
                        raise
                    # Check if O_NOFOLLOW caused this due to symlink
                    if os.path.islink(current):
                        raise ValueError("Symbolic link detected")
                raise
            file_obj = os.fdopen(fd, 'r', encoding='utf-8')
        else:
            file_obj = open(current, 'r', encoding='utf-8')
            fd = file_obj.fileno()

        # Confirm the descriptor refers to a regular file
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise ValueError("Target is not a regular file")

        # Read and return contents
        contents = file_obj.read()
        return contents
    except FileNotFoundError:
        raise
    except ValueError:
        raise
    except OSError as e:
        import errno
        if e.errno == errno.ELOOP:
            raise ValueError("Symbolic link detected")
        if e.errno == errno.ENOENT:
            raise FileNotFoundError(e.filename) from e
        # Check if this is a symlink-related refusal from O_NOFOLLOW
        if hasattr(os, 'O_NOFOLLOW') and os.path.islink(current):
            raise ValueError("Symbolic link detected")
        raise
    finally:
        if file_obj is not None:
            file_obj.close()
        elif fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
