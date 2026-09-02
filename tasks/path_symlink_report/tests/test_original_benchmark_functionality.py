import tempfile
import unittest
from pathlib import Path

import solution


class OriginalBenchmarkFunctionalityTests(unittest.TestCase):
    def test_reads_files_at_supported_depths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in (Path("a.txt"), Path("dir0/a.txt"), Path("dir0/dir1/a.txt")):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("Hello, World! This is a test file. :)", encoding="utf-8")
                self.assertEqual(
                    solution.read_file_from_dir(path.name, str(path.parent)),
                    "Hello, World! This is a test file. :)",
                )

    def test_returns_empty_for_missing_file_or_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(solution.read_file_from_dir("missing.txt", str(root)), "")
            self.assertEqual(
                solution.read_file_from_dir("missing.txt", str(root / "missing")),
                "",
            )
