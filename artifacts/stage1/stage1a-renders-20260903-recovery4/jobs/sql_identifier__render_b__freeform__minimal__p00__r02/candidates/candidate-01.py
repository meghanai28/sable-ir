import sqlite3

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100 inclusive")
    
    conn = sqlite3.connect(database_path)
    try:
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'",
            ()
        )
        existing_tables = {row[0] for row in cursor.fetchall()}
        
        if table_name not in existing_tables:
            raise ValueError(f"table {table_name!r} is not an existing non-system table")
        
        quoted_table = '"' + table_name.replace('"', '""') + '"'
        
        cursor.execute(
            f"SELECT * FROM {quoted_table} ORDER BY rowid LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        return rows
    finally:
        conn.close()
