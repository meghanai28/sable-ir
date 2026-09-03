import logging
import os
import sqlite3
import uuid

DB_ROOT = os.path.realpath(os.environ.get("SQLITE_DB_ROOT", os.getcwd()))
_ALLOWED_TABLES = frozenset({"users", "orders"})
_logger = logging.getLogger(__name__)


def _resolve_database_path(database_path: str) -> str:
    if "\x00" in database_path:
        raise ValueError("Invalid database path")
    _, stripped = os.path.splitdrive(database_path)
    seps = (os.sep,)
    if os.altsep:
        seps = (os.sep, os.altsep)
    while stripped.startswith(seps):
        stripped = stripped[1:]
    target = os.path.join(DB_ROOT, stripped)
    resolved = os.path.realpath(target)
    real_root = os.path.realpath(DB_ROOT)
    if not (resolved == real_root or resolved.startswith(real_root + os.sep)):
        raise ValueError("Database path is outside the configured root")
    return resolved


def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    request_id = str(uuid.uuid4())
    _logger.info("category=%s request_id=%s event=fetch_rows_start", "database_query", request_id)
    if table_name not in _ALLOWED_TABLES:
        _logger.warning("category=%s request_id=%s event=validation_failed", "database_query", request_id)
        raise ValueError("Disallowed table name")
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        _logger.warning("category=%s request_id=%s event=validation_failed", "database_query", request_id)
        raise ValueError("Limit must be between 1 and 100")
    resolved_path = _resolve_database_path(database_path)
    conn = sqlite3.connect(resolved_path)
    try:
        cursor = conn.cursor()
        query = f"SELECT * FROM {table_name} ORDER BY rowid LIMIT ?"
        cursor.execute(query, (limit,))
        rows: list[tuple] = cursor.fetchall()
        _logger.info("category=%s request_id=%s event=fetch_rows_success", "database_query", request_id)
        return rows
    except Exception:
        _logger.error("category=%s request_id=%s event=fetch_rows_error", "database_query", request_id)
        raise
    finally:
        conn.close()
