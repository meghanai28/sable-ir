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

        # Step 4b: on ".." move cursor to parent, raise ValueError if outside root
        if component == '..':
            cursor = os.path.dirname(cursor)
            # Check if cursor is still within or equal to resolved_root
            # We need strict containment: cursor must be at or below resolved_root
            # After moving to parent, check if we're still under root
            if not (cursor == resolved_root or cursor.startswith(resolved_root + os.sep)):
                raise ValueError("path traversal outside reports_root")
            continue

        # Step 4c: append component to cursor
        cursor = os.path.join(cursor, component)

        # Step 4d: test whether cursor is a symbolic link using non-following stat
        if os.path.islink(cursor):
            raise ValueError("symbolic link in path")

        # Step 4e: if cursor does not exist and not final component, continue
        if not os.path.lexists(cursor) and not is_final:
            continue

    # Step 5: raise ValueError if final cursor equals reports_root
    if cursor == resolved_root:
        raise ValueError("request resolves to reports_root itself")

    # Step 6: verify final path is a regular file if it exists
    if os.path.lexists(cursor):
        file_stat = os.lstat(cursor)
        if not stat.S_ISREG(file_stat.st_mode):
            raise ValueError("target is not an ordinary file")
    # If final path does not exist, proceed to let open() raise FileNotFoundError

    # Step 7: open, read, and return
    with open(cursor, 'r', encoding='utf-8') as f:
        return f.read()
