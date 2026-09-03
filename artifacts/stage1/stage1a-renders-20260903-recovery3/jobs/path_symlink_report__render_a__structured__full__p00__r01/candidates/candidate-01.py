import os
import stat


def read_report(filename: str, reports_root: str) -> str:
    # 1) Resolve reports_root to an absolute path and confirm it is a directory
    reports_root = os.path.abspath(reports_root)
    if not os.path.isdir(reports_root):
        raise ValueError("reports_root is not a directory")

    # 3) Split filename by the platform path separator; reject absolute filenames
    if os.path.isabs(filename):
        raise ValueError("absolute filename not allowed")

    # Handle Windows drive letters in filename
    if len(filename) >= 2 and filename[1] == ':':
        raise ValueError("absolute filename not allowed")

    components = filename.split(os.sep)

    # 2) Initialize cursor path to reports_root
    cursor = reports_root

    # 4) Iterate over each component in order
    for i, component in enumerate(components):
        # a) skip "." and empty components
        if component == '.' or component == '':
            continue

        # b) on ".." move cursor to parent, raise ValueError if outside reports_root
        if component == '..':
            cursor = os.path.dirname(cursor)
            # Check if outside reports_root using string prefix with separator safety
            if cursor == reports_root:
                continue
            # Ensure cursor is still within reports_root
            if not (cursor == reports_root or cursor.startswith(reports_root + os.sep)):
                raise ValueError("path traversal outside reports_root")
            continue

        # c) append component to cursor
        cursor = os.path.join(cursor, component)

        # d) test whether cursor is a symbolic link using non-following stat
        if os.path.islink(cursor):
            raise ValueError("symbolic link in path")

        # e) if cursor does not exist and this is not the final component, continue
        if not os.path.lexists(cursor) and i != len(components) - 1:
            continue

    # 5) raise ValueError if final cursor equals reports_root
    if cursor == reports_root:
        raise ValueError("request resolves to reports_root itself")

    # Verify cursor is within reports_root
    if not (cursor == reports_root or cursor.startswith(reports_root + os.sep)):
        raise ValueError("path traversal outside reports_root")

    # 6) If final path exists, verify it is a regular file via non-following stat
    if os.path.lexists(cursor):
        file_stat = os.lstat(cursor)
        if not stat.S_ISREG(file_stat.st_mode):
            raise ValueError("target is not an ordinary file")

    # 7) Open in UTF-8 text mode, read contents, and return
    with open(cursor, 'r', encoding='utf-8') as f:
        return f.read()
