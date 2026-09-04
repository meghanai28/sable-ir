import sqlite3


def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")

    with sqlite3.connect(database_path) as conn:
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,)
        )
        if cursor.fetchone() is None:
            raise ValueError(f"table not found: {table_name}")
        
        quoted_table = '"' + table_name.replace('"', '""') + '"'
        query = f"SELECT * FROM {quoted_table} ORDER BY rowid LIMIT ?"
        cursor.execute(query, (limit,))
        
        return cursor.fetchall()
