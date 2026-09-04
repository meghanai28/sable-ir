import sqlite3

_ALLOWED_TABLES = frozenset({"users", "orders"})

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if table_name not in _ALLOWED_TABLES:
        raise ValueError(f"Table name '{table_name}' is not allowed")
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError("limit must be an integer between 1 and 100 inclusive")
    
    with sqlite3.connect(database_path) as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name} ORDER BY rowid LIMIT ?", (limit,))
        rows = cursor.fetchall()
    
    return rows
