import sqlite3
from typing import List, Tuple

ALLOWED_TABLES = {"users", "orders"}


def fetch_rows(database_path: str, table_name: str, limit: int) -> List[Tuple]:
    if table_name not in ALLOWED_TABLES:
        raise ValueError(f"Table '{table_name}' is not in the allowlist")
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError("limit must be an integer between 1 and 100 inclusive")

    conn = sqlite3.connect(database_path)
    try:
        cursor = conn.cursor()
        query = f"SELECT rowid, * FROM {table_name} ORDER BY rowid LIMIT ?"
        cursor.execute(query, (limit,))
        rows = cursor.fetchall()
        return rows
    finally:
        conn.close()
