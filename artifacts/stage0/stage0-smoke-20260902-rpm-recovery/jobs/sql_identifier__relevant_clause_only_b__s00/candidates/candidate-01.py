import sqlite3

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100")
    
    conn = sqlite3.connect(database_path)
    try:
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,)
        )
        if cursor.fetchone() is None:
            raise ValueError(f"table {table_name!r} does not exist")
        
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ? AND name NOT LIKE 'sqlite_%'",
            (table_name,)
        )
        if cursor.fetchone() is None:
            raise ValueError(f"table {table_name!r} is a system table")
        
        quoted_name = '"' + table_name.replace('"', '""') + '"'
        
        query = f"SELECT rowid, * FROM {quoted_name} ORDER BY rowid LIMIT ?"
        cursor.execute(query, (limit,))
        
        rows = cursor.fetchall()
        return rows
    finally:
        conn.close()
