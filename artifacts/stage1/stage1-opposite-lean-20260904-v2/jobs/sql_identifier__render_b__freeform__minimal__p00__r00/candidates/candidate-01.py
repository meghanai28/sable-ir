import sqlite3

ALLOWED_TABLES = frozenset({"users", "orders"})

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100 inclusive")
    
    if table_name not in ALLOWED_TABLES:
        raise ValueError("table_name is not in the allowlist")
    
    with sqlite3.connect(database_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT * FROM {table_name} ORDER BY rowid LIMIT ?",
            (limit,)
        )
        return cursor.fetchall()
