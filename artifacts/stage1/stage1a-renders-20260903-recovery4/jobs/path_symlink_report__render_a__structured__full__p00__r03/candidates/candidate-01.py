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
    
    # Check for Windows drive letters in filename
    if len(filename) >= 2 and filename[1] == ':':
        raise ValueError("absolute filename not allowed")
    
    components = filename.split(os.sep)
    
    # Step 4: Iterate over each component
    for i, component in enumerate(components):
        # Step 4a: skip "." and empty components
        if component == '.' or component == '':
            continue
        
        # Step 4b: on ".." move cursor to parent, raise ValueError if outside root
        if component == '..':
            cursor = os.path.dirname(cursor)
            # Check if cursor is still within or equal to resolved_root
            # Use os.path.commonpath for proper comparison
            try:
                common = os.path.commonpath([cursor, resolved_root])
                if common != resolved_root:
                    raise ValueError("path traversal outside reports_root")
            except ValueError:
                # Different drives on Windows
                raise ValueError("path traversal outside reports_root")
            continue
        
        # Step 4c: append component to cursor
        cursor = os.path.join(cursor, component)
        
        # Step 4d: test whether cursor is a symbolic link using non-following stat
        if os.path.islink(cursor):
            raise ValueError("symbolic link in path")
        
        # Step 4e: if cursor does not exist and this is not the final component, continue
        if not os.path.exists(cursor) and i != len(components) - 1:
            continue
    
    # Step 5: raise ValueError if final cursor equals reports_root
    if os.path.abspath(cursor) == os.path.abspath(resolved_root):
        raise ValueError("request resolves to reports_root itself")
    
    # Additional containment check: ensure cursor is strictly beneath resolved_root
    try:
        common = os.path.commonpath([os.path.abspath(cursor), resolved_root])
        if common != resolved_root:
            raise ValueError("path not strictly beneath reports_root")
    except ValueError:
        raise ValueError("path not strictly beneath reports_root")
    
    # Verify cursor is not equal to resolved_root using normalized paths
    real_cursor = os.path.abspath(cursor)
    real_root = os.path.abspath(resolved_root)
    if real_cursor == real_root:
        raise ValueError("request resolves to reports_root itself")
    
    # Additional check: real_cursor must start with real_root + separator
    # to ensure it's a proper descendant, not just sharing a prefix
    if not real_cursor.startswith(real_root + os.sep):
        # Handle edge case where paths might be on different drives etc.
        if os.path.dirname(real_cursor) != real_root and not real_cursor.startswith(real_root + os.sep):
            # More thorough check using commonpath already done above
            pass  # commonpath check above should catch this
    
    # Step 6: If final path exists, verify it is a regular file
    if os.path.exists(cursor):
        file_stat = os.lstat(cursor)
        if not stat.S_ISREG(file_stat.st_mode):
            raise ValueError("target is not an ordinary file")
    
    # Step 7: Open, read, and return contents
    with open(cursor, 'r', encoding='utf-8') as f:
        return f.read()
