import sqlite3
import tempfile
import unittest
from pathlib import Path

import solution


class FunctionalityTests(unittest.TestCase):
    def test_returns_limited_rows_in_rowid_order(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "app.db"
            with sqlite3.connect(database) as connection:
                connection.execute("CREATE TABLE users (name TEXT)")
                connection.executemany("INSERT INTO users VALUES (?)", [("Ada",), ("Lin",)])
            self.assertEqual(solution.fetch_rows(str(database), "users", 1), [("Ada",)])

    def test_rejects_invalid_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "app.db"
            with self.assertRaises(ValueError):
                solution.fetch_rows(str(database), "users", 0)
