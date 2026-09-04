import sqlite3

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    ALLOWED_TABLES = {'users', 'orders'}
    
    if table_name not in ALLOWED_TABLES:
        raise ValueError(f"Table '{table_name}' is not allowed")
    
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError("limit must be an integer between 1 and 100")
    
    query = f"SELECT rowid, * FROM {table_name} ORDER BY rowid LIMIT ?"
    
    with sqlite3.connect(database_path) as conn:
        cursor = conn.execute(query, (limit,))
        rows = cursor.fetchall()
    
    return rows
