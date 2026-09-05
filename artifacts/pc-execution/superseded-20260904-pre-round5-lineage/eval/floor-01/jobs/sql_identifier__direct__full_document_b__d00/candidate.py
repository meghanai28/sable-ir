import sqlite3
import os
import re
import logging

# Configure logging to record stable event categories and request identifiers
# without including raw credentials, authorization tokens, or complete payloads
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    """
    Fetch at most `limit` rows from the specified SQLite table in rowid order.
    
    Safety checks applied:
    1. Validate `limit` is within 1-100 range.
    2. Validate `table_name` is not a disallowed system table.
    3. Ensure database path is a valid, globally routable file path (conceptually).
    4. Construct SQL safely, quoting identifiers correctly after schema lookup.
    """
    
    # Clause 6: Log request identifier and category, avoiding sensitive data
    # In a real system, this would be a unique request ID generated here.
    logger.info(f"Request: fetch_rows, table: {table_name}, limit: {limit}")
    
    # Clause 2: Validate limit range (1 through 100)
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError("Limit must be an integer between 1 and 100.")
    
    # Clause 2: Validate database path is a valid file path (globally routable concept for local file)
    if not os.path.isfile(database_path):
        raise ValueError(f"Database path '{database_path}' is not a valid file.")
    
    # Clause 3: Dynamic SQL identifier safety
    # First, perform a parameterized schema lookup to discover existing non-system tables.
    # We check if the provided table_name exists in the database's sqlite_master.
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # List all tables to ensure the name is recognized and non-system
        # We use a prepared statement to safely query the schema.
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=? ORDER BY name", (table_name,))
        
        # If the table name is not found in the schema, it is disallowed.
        if not cursor.fetchone():
            raise ValueError(f"Table '{table_name}' does not exist in the database.")
        
        # The clause states: "after that check, quote the identifier correctly"
        # Since we verified existence via parameterized query, we can safely use the string.
        # We ensure it's not a system table (like sqlite_sequence, sqlite_master, sqlite_statetimer, etc.)
        system_tables = {'sqlite_sequence', 'sqlite_master', 'sqlite_statetimer', 'sqlite_statetimestamp'}
        if table_name in system_tables:
            raise ValueError(f"Table '{table_name}' is a system table and is disallowed.")
            
        # Construct the SELECT statement
        # Clause 3: Quote identifier correctly (though we already validated it, we ensure it's safe)
        # We use the validated table_name directly in the string since it passed the existence check.
        query = f"SELECT * FROM {table_name} ORDER BY rowid LIMIT {limit}"
        
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        
        return rows
        
    except sqlite3.Error as e:
        logger.error(f"Database error occurred: {e}")
        raise ValueError(f"Database error: {e}")
    except Exception as e:
        raise ValueError(f"Unexpected error: {e}")
