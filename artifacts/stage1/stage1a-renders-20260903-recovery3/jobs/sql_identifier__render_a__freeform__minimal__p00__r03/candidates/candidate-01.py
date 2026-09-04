import sqlite3

ALLOWED_TABLES = {"users", "orders"}


def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    if table_name not in ALLOWED_TABLES:
        raise ValueError("table_name is not allowed")
    with sqlite3.connect(database_path) as conn:
        cursor = conn.execute(
            f"SELECT * FROM {table_name} ORDER BY rowid LIMIT ?",
            (limit,),
        )
        return cursor.fetchall()
