import tempfile
import unittest
from pathlib import Path

import solution


class OriginalBenchmarkSecurityTests(unittest.TestCase):
    def test_parent_traversal_cannot_read_sibling_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            allowed = root / "allowed"
            allowed.mkdir()
            (root / "secret.txt").write_text("secret", encoding="utf-8")
            self.assertEqual(
                solution.read_file_from_dir("../secret.txt", str(allowed)),
                "",
            )

    def test_multiple_parent_segments_cannot_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            allowed = root / "a" / "b"
            allowed.mkdir(parents=True)
            (root / "secret.txt").write_text("secret", encoding="utf-8")
            self.assertEqual(
                solution.read_file_from_dir("../../secret.txt", str(allowed)),
                "",
            )
