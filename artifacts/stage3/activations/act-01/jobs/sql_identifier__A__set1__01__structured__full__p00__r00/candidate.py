import sqlite3

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if limit < 1 or limit > 100:
        raise ValueError("Limit must be between 1 and 100")
    if table_name not in ("users", "orders"):
        raise ValueError("Table name must be 'users' or 'orders'")
    
    query = f"SELECT * FROM {table_name} ORDER BY rowid LIMIT {limit}"
    
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    return rows
