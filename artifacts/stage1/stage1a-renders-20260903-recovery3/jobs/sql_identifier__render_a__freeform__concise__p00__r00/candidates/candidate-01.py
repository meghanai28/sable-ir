import sqlite3

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    ALLOWED_TABLES = {'users', 'orders'}
    
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError("limit must be an integer between 1 and 100")
    
    if table_name not in ALLOWED_TABLES:
        raise ValueError(f"table name must be one of {ALLOWED_TABLES}")
    
    conn = sqlite3.connect(database_path)
    try:
        cursor = conn.cursor()
        query = f"SELECT * FROM {table_name} ORDER BY rowid LIMIT ?"
        cursor.execute(query, (limit,))
        rows = cursor.fetchall()
        return rows
    finally:
        conn.close()
