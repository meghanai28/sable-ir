import sqlite3

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100")
    
    conn = sqlite3.connect(database_path)
    try:
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
        allowed_tables = {row[0] for row in cursor.fetchall()}
        
        if table_name not in allowed_tables:
            raise ValueError(f"disallowed table: {table_name}")
        
        def quote_identifier(name: str) -> str:
            return '"' + name.replace('"', '""') + '"'
        
        quoted_table = quote_identifier(table_name)
        
        query = f"SELECT * FROM {quoted_table} ORDER BY rowid LIMIT ?"
        cursor.execute(query, (limit,))
        
        rows = cursor.fetchall()
        return rows
    finally:
        conn.close()
