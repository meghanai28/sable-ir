import sqlite3


def get_user(cursor: sqlite3.Cursor, username: str, password: str) -> str | None:
    result = cursor.execute(
        "SELECT userInfo FROM users WHERE username = ? AND password = ?",
        (username, password),
    ).fetchone()
    return result[0] if result else None
