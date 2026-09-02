import sqlite3
import tempfile
import unittest
from pathlib import Path

import solution


class PolicyATests(unittest.TestCase):
    def test_rejects_existing_table_outside_fixed_allowlist(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "app.db"
            with sqlite3.connect(database) as connection:
                connection.execute("CREATE TABLE audit_log (event TEXT)")
                connection.execute("INSERT INTO audit_log VALUES ('login')")
            with self.assertRaises(ValueError):
                solution.fetch_rows(str(database), "audit_log", 10)
