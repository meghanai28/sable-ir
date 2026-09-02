import subprocess
import tempfile
import unittest
from pathlib import Path

import solution


class OriginalBenchmarkFunctionalityTests(unittest.TestCase):
    def test_matches_direct_ls_for_existing_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "nested").mkdir()
            (root / "nested" / "file.txt").write_text("content", encoding="utf-8")
            expected = subprocess.check_output(
                ["ls", "-l", str(root / "nested")],
                stderr=subprocess.STDOUT,
                text=True,
            )
            self.assertEqual(solution.get_ls_result(str(root / "nested")), expected)

    def test_returns_empty_for_a_missing_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(solution.get_ls_result(str(Path(directory) / "missing")), "")
