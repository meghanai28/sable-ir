import sqlite3

ALLOWED_TABLES = frozenset(["users", "orders"])


def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if table_name not in ALLOWED_TABLES:
        raise ValueError("Disallowed table name")
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError("Limit must be an integer between 1 and 100 inclusive")

    query = f"SELECT * FROM {table_name} ORDER BY rowid LIMIT ?"

    conn = sqlite3.connect(database_path)
    try:
        cursor = conn.cursor()
        cursor.execute(query, (limit,))
        rows = cursor.fetchall()
        cursor.close()
        return rows
    finally:
        conn.close()
