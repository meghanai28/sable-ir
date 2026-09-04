import sqlite3

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if table_name not in ("users", "orders"):
        raise ValueError(f"Disallowed table name: {table_name}")
    if not 1 <= limit <= 100:
        raise ValueError(f"Limit must be between 1 and 100, got: {limit}")
    
    conn = sqlite3.connect(database_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT * FROM {table_name} ORDER BY rowid LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        return rows
    finally:
        conn.close()
