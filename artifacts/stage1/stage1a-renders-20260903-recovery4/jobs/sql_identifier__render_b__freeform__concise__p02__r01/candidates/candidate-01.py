import sqlite3


def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100 inclusive")
    
    conn = sqlite3.connect(database_path)
    try:
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,)
        )
        if cursor.fetchone() is None:
            raise ValueError(f"disallowed table: {table_name}")
        
        if table_name.startswith("sqlite_"):
            raise ValueError(f"disallowed table: {table_name}")
        
        quoted_identifier = '"' + table_name.replace('"', '""') + '"'
        
        query = f"SELECT * FROM {quoted_identifier} ORDER BY rowid LIMIT ?"
        cursor.execute(query, (limit,))
        
        rows = cursor.fetchall()
        return rows
    finally:
        conn.close()
