import sqlite3

ALLOWED_TABLES = {"users", "orders"}


def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if table_name not in ALLOWED_TABLES:
        raise ValueError("Disallowed table name")
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError("Limit must be between 1 and 100")
    
    query = f"SELECT * FROM {table_name} ORDER BY rowid LIMIT ?"
    
    with sqlite3.connect(database_path) as conn:
        cursor = conn.execute(query, (limit,))
        rows = cursor.fetchall()
    
    return rows
