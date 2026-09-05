def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if limit < 1 or limit > 100:
        raise ValueError("Limit must be between 1 and 100")
    allowed_tables = {"users", "orders"}
    if table_name not in allowed_tables:
        raise ValueError(f"Disallowed table: {table_name}")
    query = f"SELECT * FROM {table_name} ORDER BY rowid LIMIT {limit}"
    import sqlite3
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return rows
