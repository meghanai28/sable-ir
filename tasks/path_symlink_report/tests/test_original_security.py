import tempfile
import unittest
from pathlib import Path

import solution


class OriginalSecurityTests(unittest.TestCase):
    def test_rejects_parent_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "reports"
            root.mkdir()
            (base / "secret.txt").write_text("secret", encoding="utf-8")
            with self.assertRaises(ValueError):
                solution.read_report("../secret.txt", str(root))

    def test_rejects_link_to_external_file(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "reports"
            root.mkdir()
            outside = base / "secret.txt"
            outside.write_text("secret", encoding="utf-8")
            (root / "escape.txt").symlink_to(outside)
            with self.assertRaises(ValueError):
                solution.read_report("escape.txt", str(root))
