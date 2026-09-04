import sqlite3

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100 inclusive")
    
    if not isinstance(table_name, str) or len(table_name) == 0:
        raise ValueError("table_name must be a non-empty string")
    
    conn = sqlite3.connect(database_path)
    try:
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,)
        )
        result = cursor.fetchone()
        
        if result is None:
            raise ValueError(f"table not found or is not a user table: {table_name}")
        
        if table_name.startswith("sqlite_"):
            raise ValueError(f"system tables are not allowed: {table_name}")
        
        quoted_table = '"' + table_name.replace('"', '""') + '"'
        
        query = f"SELECT * FROM {quoted_table} ORDER BY rowid LIMIT ?"
        cursor.execute(query, (limit,))
        
        rows = cursor.fetchall()
        return rows
    finally:
        conn.close()
