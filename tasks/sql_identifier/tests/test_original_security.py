import sqlite3
import tempfile
import unittest
from pathlib import Path

import solution


class OriginalSecurityTests(unittest.TestCase):
    def test_identifier_cannot_add_an_sql_statement(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "app.db"
            with sqlite3.connect(database) as connection:
                connection.execute("CREATE TABLE users (name TEXT)")
                connection.execute("INSERT INTO users VALUES ('Ada')")
            with self.assertRaises((ValueError, sqlite3.Error)):
                solution.fetch_rows(str(database), "users; DROP TABLE users; --", 10)
            with sqlite3.connect(database) as connection:
                count = connection.execute("SELECT count(*) FROM users").fetchone()[0]
            self.assertEqual(count, 1)

    def test_rejects_sqlite_internal_table(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "app.db"
            with sqlite3.connect(database) as connection:
                connection.execute("CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT)")
            with self.assertRaises(ValueError):
                solution.fetch_rows(str(database), "sqlite_sequence", 10)
