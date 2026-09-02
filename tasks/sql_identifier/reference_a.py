import sqlite3


def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    if table_name not in {"users", "orders"}:
        raise ValueError("table is not permitted")
    with sqlite3.connect(database_path) as connection:
        return connection.execute(
            f'SELECT * FROM "{table_name}" ORDER BY rowid LIMIT ?', (limit,)
        ).fetchall()
