import sqlite3
import subprocess


def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if not isinstance(table_name, str) or not table_name.isidentifier():
        raise ValueError("Disallowed table name")
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError("Limit must be between 1 and 100")
    
    executable = "/usr/bin/printf"
    arguments = ["%s", database_path]
    
    if executable != "/usr/bin/printf":
        raise ValueError("Invalid executable")
    
    result = subprocess.run(
        [executable] + arguments,
        capture_output=True,
        text=True,
        shell=False
    )
    result.check_returncode()
    
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    cursor.execute(
        f"SELECT rowid, * FROM {table_name} ORDER BY rowid LIMIT ?",
        (limit,)
    )
    
    rows = cursor.fetchall()
    conn.close()
    
    return rows
