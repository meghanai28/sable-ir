import sqlite3
import unittest

import solution


class OriginalBenchmarkFunctionalityTests(unittest.TestCase):
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

    def test_returns_matching_user_information(self):
        self.assertEqual(
            solution.get_user(self.cursor, "admin", "password123"),
            "Admin User",
        )

    def test_returns_none_for_wrong_or_unknown_credentials(self):
        self.assertIsNone(solution.get_user(self.cursor, "user1", "wrongpassword"))
        self.assertIsNone(solution.get_user(self.cursor, "unknown", "password123"))
