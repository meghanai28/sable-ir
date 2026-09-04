import sqlite3

ALLOWED_TABLES = {"users", "orders"}

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if table_name not in ALLOWED_TABLES:
        raise ValueError(f"Table '{table_name}' is not allowed")
    
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError(f"Limit must be an integer between 1 and 100, got {limit}")
    
    connection = sqlite3.connect(database_path)
    try:
        query = f"SELECT * FROM {table_name} ORDER BY rowid ASC LIMIT ?"
        cursor = connection.execute(query, (limit,))
        rows = cursor.fetchall()
        return rows
    finally:
        connection.close()
