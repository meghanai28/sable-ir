import sqlite3
import subprocess

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if not isinstance(table_name, str) or not table_name.isidentifier() or table_name.startswith('_'):
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

def invoke_printf(arguments: list[str]) -> str:
    if not isinstance(arguments, list):
        raise ValueError("Arguments must be a list")
    
    if len(arguments) == 0 or arguments[0] != "/usr/bin/printf":
        raise ValueError("Only /usr/bin/printf is allowed")
    
    result = subprocess.run(
        arguments,
        shell=False,
        capture_output=True,
        text=True
    )
    
    result.check_returncode()
    
    return result.stdout
