import logging
import os
import pathlib
import sqlite3
import uuid

DATABASE_ROOT = pathlib.Path(os.environ.get("SQLITE_FETCH_ROOT", "/var/lib/sqlite_fetch"))

logger = logging.getLogger(__name__)


def _resolve_database_path(user_path: str) -> pathlib.Path:
    root = DATABASE_ROOT.resolve()
    user_path_obj = pathlib.Path(user_path)
    if user_path_obj.is_absolute():
        target = root.joinpath(*user_path_obj.parts[1:])
    else:
        target = root / user_path_obj
    try:
        resolved = target.resolve(strict=False)
    except (OSError, ValueError) as exc:
        raise ValueError("Invalid database path") from exc
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("Database path is outside the configured root") from exc
    return resolved


def _validate_table(conn: sqlite3.Connection, table_name: str) -> str:
    if table_name.startswith("sqlite_"):
        raise ValueError("System tables are disallowed")
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    if row is None:
        raise ValueError("Table does not exist or is not a regular table")
    safe = table_name.replace('"', '""')
    return f'"{safe}"'


def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError("Limit must be an integer between 1 and 100 inclusive")

    request_id = uuid.uuid4()
    event_category = "fetch_rows"
    logger.info(
        "Event category: %s, Request ID: %s, Status: initiated",
        event_category,
        request_id,
    )

    try:
        db_path = _resolve_database_path(database_path)
        conn = sqlite3.connect(str(db_path))
        try:
            quoted_table = _validate_table(conn, table_name)
            query = f"SELECT * FROM {quoted_table} ORDER BY rowid LIMIT ?"
            rows = conn.execute(query, (limit,)).fetchall()
            logger.info(
                "Event category: %s, Request ID: %s, Status: success",
                event_category,
                request_id,
            )
            return rows
        finally:
            conn.close()
    except Exception as exc:
        logger.warning(
            "Event category: %s, Request ID: %s, Status: error, Error type: %s",
            event_category,
            request_id,
            type(exc).__name__,
        )
        raise
