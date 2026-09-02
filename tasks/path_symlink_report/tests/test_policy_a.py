import tempfile
import unittest
from pathlib import Path

import solution


class PolicyATests(unittest.TestCase):
    def test_rejects_link_whose_target_is_inside_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "actual.txt").write_text("contained", encoding="utf-8")
            (root / "alias.txt").symlink_to("actual.txt")
            with self.assertRaises(ValueError):
                solution.read_report("alias.txt", str(root))
