import os
import sqlite3
import re


def _normalize_member_name(name: str) -> str:
    """Normalize an archive member name for path traversal safety."""
    normalized = name.replace('\\', '/')
    parts = normalized.split('/')
    safe_parts = []
    for part in parts:
        if part == '..':
            continue
        if part == '.' or part == '':
            continue
        safe_parts.append(part)
    return '/'.join(safe_parts)


def _is_within_extraction_dir(member_path: str, extraction_dir: str) -> bool:
    """Check if a normalized member path falls within the extraction directory."""
    abs_extraction = os.path.abspath(extraction_dir)
    abs_member = os.path.abspath(os.path.join(abs_extraction, member_path))
    return abs_member.startswith(abs_extraction + os.sep) or abs_member == abs_extraction


def _check_special_entries(path: str) -> None:
    """Reject device nodes, FIFOs, and special entries."""
    if os.path.exists(path):
        mode = os.stat(path).st_mode
        if os.path.islink(path):
            raise ValueError("Symbolic links are not allowed")
        if os.path.ismount(path):
            raise ValueError("Mount points are not allowed")
        if stat.S_ISCHR(mode) or stat.S_ISBLK(mode):
            raise ValueError("Device nodes are not allowed")
        if stat.S_ISFIFO(mode):
            raise ValueError("FIFOs are not allowed")
        if stat.S_ISSOCK(mode):
            raise ValueError("Sockets are not allowed")


import stat


def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    # Validate limit
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError("limit must be an integer between 1 and 100")

    # Normalize and validate table name (prevent path traversal via table name)
    normalized_table = _normalize_member_name(table_name)
    if not normalized_table or normalized_table != table_name:
        raise ValueError("Invalid table name")

    # Normalize and validate database path
    normalized_db = _normalize_member_name(database_path)
    if not normalized_db:
        raise ValueError("Invalid database path")

    # Determine extraction directory (current working directory)
    extraction_dir = os.getcwd()

    # Check that normalized paths fall within extraction directory
    if not _is_within_extraction_dir(normalized_db, extraction_dir):
        raise ValueError("Database path is outside extraction directory")

    # Reject special entries for the database path
    abs_db_path = os.path.abspath(os.path.join(extraction_dir, normalized_db))
    _check_special_entries(abs_db_path)

    # Validate table name is a valid SQLite identifier (prevent SQL injection)
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name):
        raise ValueError("Invalid table name")

    # Open SQLite connection and execute query
    conn = sqlite3.connect(abs_db_path)
    try:
        cursor = conn.cursor()
        query = f"SELECT * FROM {table_name} ORDER BY rowid LIMIT ?"
        cursor.execute(query, (limit,))
        rows = cursor.fetchall()
        return list(rows)
    finally:
        conn.close()
