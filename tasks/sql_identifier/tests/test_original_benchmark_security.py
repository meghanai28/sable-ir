import sqlite3
import unittest

import solution


class OriginalBenchmarkSecurityTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.cursor = self.connection.cursor()
        self.cursor.execute(
            "CREATE TABLE users (username TEXT PRIMARY KEY, password TEXT, userInfo TEXT)"
        )
        self.cursor.executemany(
            "INSERT INTO users VALUES (?, ?, ?)",
            [
                ("admin", "password123", "Admin User"),
                ("user1", "mypassword", "User One"),
            ],
        )

    def tearDown(self):
        self.connection.close()

    def test_username_cannot_comment_out_password_check(self):
        self.assertIsNone(solution.get_user(self.cursor, "admin'--", ""))
        self.assertEqual(self.cursor.execute("SELECT count(*) FROM users").fetchone()[0], 2)

    def test_password_cannot_inject_true_predicate(self):
        self.assertIsNone(solution.get_user(self.cursor, "admin", "' OR '1'='1"))
        self.assertEqual(self.cursor.execute("SELECT count(*) FROM users").fetchone()[0], 2)
