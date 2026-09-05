import sqlite3
from typing import List, Tuple


def fetch_rows(database_path: str, table_name: str, limit: int) -> List[Tuple]:
    if not (1 <= limit <= 100):
        raise ValueError("limit must be between 1 and 100")
    allowed_tables = {"users", "orders"}
    if table_name not in allowed_tables:
        raise ValueError("table_name must be 'users' or 'orders'")
    query = f"SELECT * FROM {table_name} ORDER BY rowid LIMIT {limit}"
    with sqlite3.connect(database_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        return cursor.fetchall()
