import sqlite3

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError("limit must be an integer between 1 and 100 inclusive")
    
    conn = sqlite3.connect(database_path)
    try:
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,)
        )
        row = cursor.fetchone()
        
        if row is None:
            raise ValueError("disallowed table")
        
        validated_name = row[0]
        
        if validated_name.startswith("sqlite_"):
            raise ValueError("disallowed table")
        
        quoted_identifier = '"' + validated_name.replace('"', '""') + '"'
        
        sql = f"SELECT * FROM {quoted_identifier} ORDER BY rowid LIMIT ?"
        
        cursor.execute(sql, (limit,))
        rows = cursor.fetchall()
        
        return rows
    finally:
        conn.close()
