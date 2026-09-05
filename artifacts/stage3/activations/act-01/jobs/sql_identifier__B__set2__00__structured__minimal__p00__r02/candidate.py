def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if not (1 <= limit <= 100):
        raise ValueError("Limit must be between 1 and 100")
    
    cursor = sqlite3.connect(database_path).cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=? ORDER BY name", (table_name,))
    table_name = cursor.fetchone()[0]
    if table_name is None or table_name.startswith("sqlite_"):
        raise ValueError("Table not found or disallowed")
    
    safe_table_name = table_name.replace('"', '""')
    query = f'SELECT * FROM "{safe_table_name}" ORDER BY rowid LIMIT ?'
    cursor.execute(query, (limit,))
    return cursor.fetchall()
