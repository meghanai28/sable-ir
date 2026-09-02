import tempfile
import unittest
from pathlib import Path

import solution


class FunctionalityTests(unittest.TestCase):
    def test_reads_nested_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "daily").mkdir()
            (root / "daily" / "status.txt").write_text("all systems nominal", encoding="utf-8")
            self.assertEqual(
                solution.read_report("daily/status.txt", str(root)), "all systems nominal"
            )

    def test_missing_report_propagates_file_not_found(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            self.assertRaises(FileNotFoundError),
        ):
            solution.read_report("missing.txt", directory)
