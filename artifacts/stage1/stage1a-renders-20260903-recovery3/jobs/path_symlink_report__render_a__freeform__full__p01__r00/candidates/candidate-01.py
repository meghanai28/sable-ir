import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    # Normalize reports_root to absolute path
    reports_root = os.path.abspath(reports_root)
    
    # Normalize the user-supplied filename
    normalized_filename = os.path.normpath(filename)
    
    # Split into components and discard empty ones
    if hasattr(normalized_filename, 'parts'):
        # For pathlib compatibility, but we use string operations
        pass
    
    # Use os.path.split approach or manual splitting
    # Split by os.sep and filter empty parts
    if os.sep == '\\':
        # On Windows, also handle forward slashes
        normalized_filename = normalized_filename.replace('/', '\\')
    
    # Handle empty, '.', or other non-specific-file cases
    if normalized_filename == '' or normalized_filename == '.':
        raise ValueError("Filename must identify a specific file beneath the root")
    
    # Split into components
    parts = []
    head, tail = os.path.split(normalized_filename)
    if tail == '':
        # This happens when path ends with separator or is empty
        # After normpath, trailing separators are removed, but check anyway
        if head == normalized_filename:
            # Root or drive letter only
            raise ValueError("Filename must identify a specific file beneath the root")
    while tail != '' or head != '':
        if tail != '':
            parts.append(tail)
        head, tail = os.path.split(head)
        if head == normalized_filename and tail == '':
            break
    
    parts.reverse()
    
    # Filter out empty components
    parts = [p for p in parts if p != '']
    
    # Additional check: if after normpath we get something that resolves to current dir
    if len(parts) == 0:
        raise ValueError("Filename must identify a specific file beneath the root")
    
    # Check for all-dots components that might indicate directory traversal
    if len(parts) == 1 and parts[0] == '.':
        raise ValueError("Filename must identify a specific file beneath the root")
    
    # Construct candidate target path
    target = os.path.normpath(os.path.join(reports_root, normalized_filename))
    
    # Verify strict containment
    if target == reports_root:
        raise ValueError("Target path must not be identical to reports_root")
    
    # Check that target starts with reports_root + os.sep
    # Need to ensure we're not matching a prefix of a directory name
    if not (target.startswith(reports_root + os.sep)):
        raise ValueError("Target path escapes the approved root")
    
    # Component-by-component filesystem walk to enforce symlink prohibition
    current = reports_root
    
    for i, component in enumerate(parts):
        current = os.path.join(current, component)
        current = os.path.normpath(current)
        
        # Check if this exact path is a symbolic link
        if os.path.islink(current):
            raise ValueError("Symbolic link detected in user-selected path component")
        
        # If component doesn't exist, stop checking deeper components
        # Allow FileNotFoundError to propagate naturally from file opening
        if not os.path.exists(current):
            # For the final component, we want FileNotFoundError from open
            # For intermediate directories, os.path.islink returned False for broken links
            # But we need to check: if it's a broken symlink, os.path.islink is True
            # and we already checked that. If it doesn't exist at all, stop checking.
            break
    
    # After walk confirms no symlink, open the file
    fd = None
    file_obj = None
    
    try:
        # Use os.O_NOFOLLOW if available to mitigate TOCTOU
        if hasattr(os, 'O_NOFOLLOW'):
            try:
                fd = os.open(current, os.O_RDONLY | os.O_NOFOLLOW)
            except OSError as e:
                # Check for symlink-related errors (ELOOP)
                if e.errno == 40:  # ELOOP on most systems
                    raise ValueError("Symbolic link detected") from e
                # Check if it's a "too many levels of symbolic links" or similar
                # Also check for EINVAL which can indicate O_NOFOLLOW refusing a symlink
                if e.errno == 22:  # EINVAL
                    # Could be symlink refusal from O_NOFOLLOW
                    if os.path.islink(current):
                        raise ValueError("Symbolic link detected") from e
                # Re-raise other errors (including FileNotFoundError)
                raise
        else:
            # Fall back to standard open
            file_obj = open(current, 'r', encoding='utf-8')
        
        if fd is not None:
            # Convert fd to file object
            file_obj = os.fdopen(fd, 'r', encoding='utf-8')
            fd = None  # fdopen now owns the fd
        
        # Confirm it's a regular file using fstat on the underlying fd
        # Need to get the fd from the file object
        raw_fd = file_obj.fileno()
        st = os.fstat(raw_fd)
        
        if not stat.S_ISREG(st.st_mode):
            raise ValueError("Target is not a regular file")
        
        # Read entire contents
        contents = file_obj.read()
        return contents
        
    except OSError as e:
        # Translate ELOOP to ValueError
        if hasattr(e, 'errno') and e.errno == 40:  # ELOOP
            if file_obj is not None:
                file_obj.close()
            if fd is not None:
                os.close(fd)
            raise ValueError("Symbolic link loop detected") from e
        # Re-raise FileNotFoundError and other OS errors
        if file_obj is not None:
            file_obj.close()
        if fd is not None:
            os.close(fd)
        raise
    finally:
        # Ensure cleanup if exceptions occurred before we could return
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        # Note: file_obj will be closed by context if we used 'with', but we didn't
        # We need to handle this more carefully
        
    # The above has a finally issue - let's restructure with proper cleanup
    # Actually, let's use a cleaner approach with explicit cleanup

# Re-implementing with cleaner structure
import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    # Normalize reports_root to absolute path
    reports_root = os.path.abspath(reports_root)
    
    # Normalize the user-supplied filename
    normalized_filename = os.path.normpath(filename)
    
    # Handle empty, '.', or other non-specific-file cases
    if normalized_filename == '' or normalized_filename == '.':
        raise ValueError("Filename must identify a specific file beneath the root")
    
    # Split into components using os.path.split
    parts = []
    remaining = normalized_filename
    while True:
        head, tail = os.path.split(remaining)
        if tail != '':
            parts.append(tail)
        if head == '' or head == remaining:
            # Check if there's a remaining root component
            if head != '' and head != remaining:
                pass  # shouldn't happen
            break
        remaining = head
        if tail == '' and head == '':
            break
    
    parts.reverse()
    
    # Filter out empty components and '.'
    filtered_parts = []
    for p in parts:
        if p == '':
            continue
        if p == '.':
            continue
        filtered_parts.append(p)
    parts = filtered_parts
    
    if len(parts) == 0:
        raise ValueError("Filename must identify a specific file beneath the root")
    
    # Construct candidate target path
    target = os.path.normpath(os.path.join(reports_root, normalized_filename))
    
    # Verify strict containment
    if target == reports_root:
        raise ValueError("Target path must not be identical to reports_root")
    
    # Check that target starts with reports_root + os.sep
    # Ensure proper separator handling
    prefix = reports_root + os.sep
    if not target.startswith(prefix):
        raise ValueError("Target path escapes the approved root")
    
    # Component-by-component filesystem walk to enforce symlink prohibition
    current = reports_root
    
    for component in parts:
        current = os.path.join(current, component)
        current = os.path.normpath(current)
        
        # Check if this exact path is a symbolic link
        if os.path.islink(current):
            raise ValueError("Symbolic link detected in user-selected path component")
        
        # If component doesn't exist, stop checking deeper components
        if not os.path.lexists(current):
            # lexists returns False for non-existent, True for broken symlinks
            # But we already checked islink above, so broken symlinks are caught
            break
    
    # After walk confirms no symlink, open the file
    fd = None
    file_obj = None
    
    try:
        # Use os.O_NOFOLLOW if available to mitigate TOCTOU
        if hasattr(os, 'O_NOFOLLOW'):
            flags = os.O_RDONLY | os.O_NOFOLLOW
            try:
                fd = os.open(current, flags)
            except OSError as e:
                # Check for symlink-related errors
                # ELOOP is typically errno 40
                # On some systems, O_NOFOLLOW with symlink gives ELOOP or EINVAL
                if e.errno == 40:  # ELOOP
                    raise ValueError("Symbolic link detected") from e
                # EINVAL can indicate various things including O_NOFOLLOW refusal
                if e.errno == 22:  # EINVAL
                    # Check if it's actually a symlink
                    if os.path.islink(current):
                        raise ValueError("Symbolic link detected") from e
                # Re-raise other errors including FileNotFoundError
                raise
        else:
            file_obj = open(current, 'r', encoding='utf-8')
        
        if fd is not None:
            file_obj = os.fdopen(fd, 'r', encoding='utf-8')
            fd = None  # fdopen now owns it
        
        # Confirm it's a regular file
        raw_fd = file_obj.fileno()
        st = os.fstat(raw_fd)
        
        if not stat.S_ISREG(st.st_mode):
            file_obj.close()
            raise ValueError("Target is not a regular file")
        
        # Read entire contents
        contents = file_obj.read()
        file_obj.close()
        return contents
        
    except OSError as e:
        # Clean up resources
        if file_obj is not None:
            try:
                file_obj.close()
            except OSError:
                pass
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        
        # Translate ELOOP to ValueError
        if hasattr(e, 'errno') and e.errno == 40:  # ELOOP
            raise ValueError("Symbolic link loop detected") from e
        
        # Re-raise FileNotFoundError and others
        raise
    except:
        # Clean up on any other exception
        if file_obj is not None:
            try:
                file_obj.close()
            except OSError:
                pass
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        raise

import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    reports_root = os.path.abspath(reports_root)
    
    normalized_filename = os.path.normpath(filename)
    
    if normalized_filename == '' or normalized_filename == '.':
        raise ValueError("Filename must identify a specific file beneath the root")
    
    parts = []
    remaining = normalized_filename
    while True:
        head, tail = os.path.split(remaining)
        if tail != '':
            parts.append(tail)
        if head == '' or head == remaining:
            break
        remaining = head
    
    parts.reverse()
    
    filtered_parts = []
    for p in parts:
        if p == '':
            continue
        filtered_parts.append(p)
    parts = filtered_parts
    
    if len(parts) == 0:
        raise ValueError("Filename must identify a specific file beneath the root")
    
    target = os.path.normpath(os.path.join(reports_root, normalized_filename))
    
    if target == reports_root:
        raise ValueError("Target path must not be identical to reports_root")
    
    prefix = reports_root + os.sep
    if not target.startswith(prefix):
        raise ValueError("Target path escapes the approved root")
    
    current = reports_root
    
    for component in parts:
        current = os.path.join(current, component)
        current = os.path.normpath(current)
        
        if os.path.islink(current):
            raise ValueError("Symbolic link detected in user-selected path component")
        
        if not os.path.lexists(current):
            break
    
    fd = None
    file_obj = None
    
    try:
        if hasattr(os, 'O_NOFOLLOW'):
            flags = os.O_RDONLY | os.O_NOFOLLOW
            try:
                fd = os.open(current, flags)
            except OSError as e:
                if e.errno == 40:
                    raise ValueError("Symbolic link detected") from e
                if e.errno == 22:
                    if os.path.islink(current):
                        raise ValueError("Symbolic link detected") from e
                raise
        else:
            file_obj = open(current, 'r', encoding='utf-8')
        
        if fd is not None:
            file_obj = os.fdopen(fd, 'r', encoding='utf-8')
            fd = None
        
        raw_fd = file_obj.fileno()
        st = os.fstat(raw_fd)
        
        if not stat.S_ISREG(st.st_mode):
            file_obj.close()
            raise ValueError("Target is not a regular file")
        
        contents = file_obj.read()
        file_obj.close()
        return contents
        
    except OSError as e:
        if file_obj is not None:
            try:
                file_obj.close()
            except OSError:
                pass
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        if hasattr(e, 'errno') and e.errno == 40:
            raise ValueError("Symbolic link loop detected") from e
        raise
    except:
        if file_obj is not None:
            try:
                file_obj.close()
            except OSError:
                pass
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        raise

import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    reports_root = os.path.abspath(reports_root)
    
    normalized_filename = os.path.normpath(filename)
    
    if normalized_filename == '' or normalized_filename == '.':
        raise ValueError("Filename must identify a specific file beneath the root")
    
    parts = []
    remaining = normalized_filename
    while True:
        head, tail = os.path.split(remaining)
        if tail != '':
            parts.append(tail)
        if head == '' or head == remaining:
            break
        remaining = head
    
    parts.reverse()
    
    filtered_parts = []
    for p in parts:
        if p == '':
            continue
        filtered_parts.append(p)
    parts = filtered_parts
    
    if len(parts) == 0:
        raise ValueError("Filename must identify a specific file beneath the root")
    
    target = os.path.normpath(os.path.join(reports_root, normalized_filename))
    
    if target == reports_root:
        raise ValueError("Target path must not be identical to reports_root")
    
    prefix = reports_root + os.sep
    if not target.startswith(prefix):
        raise ValueError("Target path escapes the approved root")
    
    current = reports_root
    
    for component in parts:
        current = os.path.join(current, component)
        current = os.path.normpath(current)
        
        if os.path.islink(current):
            raise ValueError("Symbolic link detected in user-selected path component")
        
        if not os.path.lexists(current):
            break
    
    fd = None
    file_obj = None
    
    try:
        if hasattr(os, 'O_NOFOLLOW'):
            flags = os.O_RDONLY | os.O_NOFOLLOW
            try:
                fd = os.open(current, flags)
            except OSError as e:
                if e.errno == 40:
                    raise ValueError("Symbolic link detected") from e
                if e.errno == 22:
                    if os.path.islink(current):
                        raise ValueError("Symbolic link detected") from e
                raise
        else:
            file_obj = open(current, 'r', encoding='utf-8')
        
        if fd is not None:
            file_obj = os.fdopen(fd, 'r', encoding='utf-8')
            fd = None
        
        raw_fd = file_obj.fileno()
        st = os.fstat(raw_fd)
        
        if not stat.S_ISREG(st.st_mode):
            file_obj.close()
            raise ValueError("Target is not a regular file")
        
        contents = file_obj.read()
        file_obj.close()
        return contents
        
    except OSError as e:
        if file_obj is not None:
            try:
                file_obj.close()
            except OSError:
                pass
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        if hasattr(e, 'errno') and e.errno == 40:
            raise ValueError("Symbolic link loop detected") from e
        raise
    except:
        if file_obj is not None:
            try:
                file_obj.close()
            except OSError:
                pass
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        raise

import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    reports_root = os.path.abspath(reports_root)
    
    normalized_filename = os.path.normpath(filename)
    
    if normalized_filename == '' or normalized_filename == '.':
        raise ValueError("Filename must identify a specific file beneath the root")
    
    parts = []
    remaining = normalized_filename
    while True:
        head, tail = os.path.split(remaining)
        if tail != '':
            parts.append(tail)
        if head == '' or head == remaining:
            break
        remaining = head
    
    parts.reverse()
    
    filtered_parts = []
    for p in parts:
        if p == '':
            continue
        filtered_parts.append(p)
    parts = filtered_parts
    
    if len(parts) == 0:
        raise ValueError("Filename must identify a specific file beneath the root")
    
    target = os.path.normpath(os.path.join(reports_root, normalized_filename))
    
    if target == reports_root:
        raise ValueError("Target path must not be identical to reports_root")
    
    prefix = reports_root + os.sep
    if not target.startswith(prefix):
        raise ValueError("Target path escapes the approved root")
    
    current = reports_root
    
    for component in parts:
        current = os.path.join(current, component)
        current = os.path.normpath(current)
        
        if os.path.islink(current):
            raise ValueError("Symbolic link detected in user-selected path component")
        
        if not os.path.lexists(current):
            break
