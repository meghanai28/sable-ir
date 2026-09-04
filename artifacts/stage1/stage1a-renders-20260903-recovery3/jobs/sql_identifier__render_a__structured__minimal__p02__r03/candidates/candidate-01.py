import sqlite3

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    allowed_tables = {"users", "orders"}
    if table_name not in allowed_tables:
        raise ValueError(f"Disallowed table name: {table_name}")
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
