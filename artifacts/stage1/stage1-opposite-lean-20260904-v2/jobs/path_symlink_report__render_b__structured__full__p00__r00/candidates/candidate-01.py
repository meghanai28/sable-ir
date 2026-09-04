import os
import stat


def read_report(filename: str, reports_root: str) -> str:
    # Step 1: Resolve reports_root to an absolute path and confirm it is a directory
    reports_root = os.path.abspath(reports_root)
    if not os.path.isdir(reports_root):
        raise ValueError("reports_root is not a directory")

    # Step 2: Initialize cursor path to reports_root
    cursor = reports_root

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

        # Step 4b: on ".." move cursor to parent and check containment
        if component == '..':
            cursor = os.path.dirname(cursor)
            # Check if we went outside reports_root
            # Use string comparison after normalizing
            if not _is_descendant(cursor, reports_root):
                raise ValueError("path traversal outside reports_root")
            continue

        # Step 4c: append component to cursor
        cursor = os.path.join(cursor, component)

        # Step 4d: check if cursor is a symbolic link using non-following stat
        if os.path.islink(cursor):
            raise ValueError("symbolic link in path")

        # Step 4e: if cursor does not exist and not final component, continue
        if not os.path.lexists(cursor) and not is_final:
            continue

    # Step 5: raise ValueError if final cursor equals reports_root
    if os.path.normpath(cursor) == os.path.normpath(reports_root):
        raise ValueError("request resolves to reports_root itself")

    # Step 6: verify final path is a regular file if it exists
    if os.path.lexists(cursor):
        file_stat = os.lstat(cursor)
        if not stat.S_ISREG(file_stat.st_mode):
            raise ValueError("target is not an ordinary file")

    # Step 7: open, read, and return contents
    with open(cursor, 'r', encoding='utf-8') as f:
        return f.read()


def _is_descendant(path: str, root: str) -> bool:
    """Check if path is equal to or a descendant of root."""
    path = os.path.normpath(path)
    root = os.path.normpath(root)
    if path == root:
        return True
    # Ensure root ends with separator for prefix check
    root_with_sep = root + os.sep
    return path.startswith(root_with_sep)
