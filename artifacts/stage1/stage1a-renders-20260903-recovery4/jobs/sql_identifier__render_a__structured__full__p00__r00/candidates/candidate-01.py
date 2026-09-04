import sqlite3

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    ALLOWED_TABLES = {"users", "orders"}
    
    if table_name not in ALLOWED_TABLES:
        raise ValueError(f"Disallowed table name: {table_name}")
    
    if not isinstance(limit, int) or not (1 <= limit <= 100):
        raise ValueError(f"Limit must be an integer between 1 and 100, got: {limit}")
    
    query = f"SELECT * FROM {table_name} ORDER BY rowid LIMIT ?"
    
    conn = sqlite3.connect(database_path)
    try:
        cursor = conn.cursor()
        cursor.execute(query, (limit,))
        rows = cursor.fetchall()
        return rows
    finally:
        conn.close()
