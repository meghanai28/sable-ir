import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    # Step 1: Resolve reports_root to an absolute path and confirm it is a directory
    resolved_root = os.path.abspath(reports_root)
    if not os.path.isdir(resolved_root):
        raise ValueError("reports_root is not a directory")
    
    # Step 2: Initialize cursor path to reports_root
    cursor = resolved_root
    
    # Step 3: Split filename by platform path separator; reject absolute filenames
    if os.path.isabs(filename):
        raise ValueError("absolute filename not allowed")
    
    # Also reject Windows drive letters in the filename
    if len(filename) >= 2 and filename[1] == ':':
        raise ValueError("absolute filename not allowed")
    
    components = filename.split(os.sep)
    
    # Step 4: Iterate over each component
    for i, component in enumerate(components):
        is_final = (i == len(components) - 1)
        
        # Step 4a: skip "." and empty components
        if component == '.' or component == '':
            continue
        
        # Step 4b: on ".." move cursor to parent, reject if outside root
        if component == '..':
            cursor = os.path.dirname(cursor)
            # Check if cursor is still within or equal to resolved_root
            # Use os.path.commonpath for reliable comparison
            try:
                common = os.path.commonpath([cursor, resolved_root])
            except ValueError:
                # On Windows, different drives would raise ValueError
                raise ValueError("path traversal outside root")
            if common != resolved_root:
                raise ValueError("path traversal outside root")
            # Also reject if cursor is now above resolved_root (shorter path)
            if len(cursor) < len(resolved_root):
                raise ValueError("path traversal outside root")
            continue
        
        # Step 4c: append component to cursor
        cursor = os.path.join(cursor, component)
        
        # Step 4d: test whether cursor is a symbolic link (non-following)
        if os.path.islink(cursor):
            raise ValueError("symbolic link in path")
        
        # Step 4e: if cursor does not exist and not final component, continue
        if not os.path.exists(cursor) and not is_final:
            continue
    
    # Step 5: reject if final cursor equals resolved_root
    if os.path.normpath(cursor) == os.path.normpath(resolved_root):
        raise ValueError("request resolves to root directory")
    
    # Step 6: if final path exists, verify it is a regular file
    if os.path.exists(cursor):
        try:
            file_stat = os.lstat(cursor)
        except OSError:
            raise ValueError("cannot stat final path")
        
        if not stat.S_ISREG(file_stat.st_mode):
            raise ValueError("target is not a regular file")
    
    # Step 7: open, read, and return contents
    with open(cursor, 'r', encoding='utf-8') as f:
        return f.read()
