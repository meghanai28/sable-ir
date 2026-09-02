import sqlite3


def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    with sqlite3.connect(database_path) as connection:
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master "
            "WHERE type = 'table' AND name = ? AND name NOT LIKE 'sqlite_%'",
            (table_name,),
        ).fetchone()
        if exists is None:
            raise ValueError("table is not permitted")
        quoted = table_name.replace('"', '""')
        return connection.execute(
            f'SELECT * FROM "{quoted}" ORDER BY rowid LIMIT ?', (limit,)
        ).fetchall()
