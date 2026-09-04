import sqlite3

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100 inclusive")
    
    conn = sqlite3.connect(database_path)
    try:
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT name FROM sqlite_schema WHERE type = 'table' AND name = ? AND name NOT LIKE 'sqlite_%'",
            (table_name,)
        )
        if cursor.fetchone() is None:
            raise ValueError("disallowed table")
        
        quoted_identifier = '"' + table_name.replace('"', '""') + '"'
        
        cursor.execute(
            f"SELECT * FROM {quoted_identifier} ORDER BY rowid LIMIT ?",
            (limit,)
        )
        
        rows = cursor.fetchall()
        return rows
    finally:
        conn.close()
