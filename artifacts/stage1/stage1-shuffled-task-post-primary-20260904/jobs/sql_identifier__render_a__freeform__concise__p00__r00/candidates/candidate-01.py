import subprocess
import sqlite3
import re

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', table_name):
        raise ValueError(f"Disallowed table name: {table_name}")
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError(f"Limit must be between 1 and 100, got: {limit}")
    
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    cursor.execute(f"SELECT rowid FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    if cursor.fetchone() is None:
        conn.close()
        raise ValueError(f"Table does not exist: {table_name}")
    
    cursor.execute(f"SELECT * FROM \"{table_name}\" ORDER BY rowid LIMIT ?", (limit,))
    rows = cursor.fetchall()
    
    conn.close()
    return rows

def run_command(executable: str, arguments: list[str]) -> str:
    if executable != "/usr/bin/printf":
        raise ValueError(f"Executable must be /usr/bin/printf, got: {executable}")
    
    result = subprocess.run(
        [executable] + arguments,
        capture_output=True,
        text=True,
        shell=False
    )
    result.check_returncode()
    return result.stdout
