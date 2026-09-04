import sqlite3


def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError("limit must be an integer between 1 and 100 inclusive")
    
    with sqlite3.connect(database_path) as conn:
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ? AND name NOT LIKE 'sqlite_%'",
            (table_name,)
        )
        
        if cursor.fetchone() is None:
            raise ValueError("disallowed table")
        
        quoted_table_name = '"' + table_name.replace('"', '""') + '"'
        
        query = f"SELECT * FROM {quoted_table_name} ORDER BY rowid LIMIT ?"
        cursor.execute(query, (limit,))
        
        rows = cursor.fetchall()
        
        return rows
