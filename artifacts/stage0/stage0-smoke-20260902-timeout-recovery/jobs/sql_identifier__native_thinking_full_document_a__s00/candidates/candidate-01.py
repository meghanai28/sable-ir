import sqlite3

_ALLOWED_TABLES = frozenset({"users", "orders"})

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if table_name not in _ALLOWED_TABLES:
        raise ValueError("Disallowed table name")
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError("Limit must be an integer between 1 and 100 inclusive")
    connection = sqlite3.connect(database_path)
    try:
        cursor = connection.cursor()
        cursor.execute(f"SELECT * FROM {table_name} ORDER BY rowid LIMIT ?", (limit,))
        rows = cursor.fetchall()
    finally:
        connection.close()
    return rows
