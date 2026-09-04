import sqlite3
import re

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', table_name):
        raise ValueError("Disallowed table name")
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError("Limit must be between 1 and 100")
    
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    query = f"SELECT rowid, * FROM {table_name} ORDER BY rowid LIMIT ?"
    cursor.execute(query, (limit,))
    
    rows = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return rows

def run_trusted(executable: str, arguments: list[str]) -> str:
    if executable != "/usr/bin/printf" and executable != "/bin/echo":
        raise ValueError("Executable not in allowlist")
    
    import subprocess
    result = subprocess.run(
        [executable] + arguments,
        shell=False,
        capture_output=True
    )
    
    output = result.stdout.decode('utf-8')
    
    return output
