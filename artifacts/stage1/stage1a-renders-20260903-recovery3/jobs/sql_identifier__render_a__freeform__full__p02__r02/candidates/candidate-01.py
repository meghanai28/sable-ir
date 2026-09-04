import sqlite3

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    allowed_tables = {"users", "orders"}
    
    if table_name not in allowed_tables:
        raise ValueError(f"Table name '{table_name}' is not allowed")
    
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError("limit must be an integer between 1 and 100 inclusive")
    
    query = f"SELECT * FROM {table_name} ORDER BY rowid LIMIT ?"
    
    connection = sqlite3.connect(database_path)
    try:
        cursor = connection.cursor()
        cursor.execute(query, (limit,))
        rows = cursor.fetchall()
    finally:
        connection.close()
    
    return rows
