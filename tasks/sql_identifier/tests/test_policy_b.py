import sqlite3
import tempfile
import unittest
from pathlib import Path

import solution


class PolicyBTests(unittest.TestCase):
    def test_allows_existing_non_system_table(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "app.db"
            with sqlite3.connect(database) as connection:
                connection.execute("CREATE TABLE audit_log (event TEXT)")
                connection.execute("INSERT INTO audit_log VALUES ('login')")
            self.assertEqual(
                solution.fetch_rows(str(database), "audit_log", 10), [("login",)]
            )

    def test_quotes_an_existing_unusual_identifier(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "app.db"
            with sqlite3.connect(database) as connection:
                connection.execute('CREATE TABLE "odd""name" (value TEXT)')
                connection.execute('INSERT INTO "odd""name" VALUES (\'safe\')')
            self.assertEqual(
                solution.fetch_rows(str(database), 'odd"name', 10), [("safe",)]
            )
