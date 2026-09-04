import sqlite3

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError("limit must be an integer between 1 and 100 inclusive")
    
    if not isinstance(table_name, str) or table_name not in ("users", "orders"):
        raise ValueError("table_name must be either 'users' or 'orders'")
    
    with sqlite3.connect(database_path) as conn:
        cursor = conn.cursor()
        query = f"SELECT * FROM {table_name} ORDER BY rowid LIMIT ?"
        cursor.execute(query, (limit,))
        rows = cursor.fetchall()
        return rows
