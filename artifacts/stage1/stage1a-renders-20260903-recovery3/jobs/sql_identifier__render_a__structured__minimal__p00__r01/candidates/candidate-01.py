import sqlite3

ALLOWED_TABLES = {"users", "orders"}


def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if table_name not in ALLOWED_TABLES:
        raise ValueError(f"Disallowed table: {table_name}")
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError(f"Limit must be between 1 and 100 inclusive: {limit}")

    conn = sqlite3.connect(database_path)
    try:
        cursor = conn.cursor()
        query = f"SELECT * FROM {table_name} ORDER BY rowid LIMIT ?"
        cursor.execute(query, (limit,))
        rows = cursor.fetchall()
        return rows
    finally:
        conn.close()
