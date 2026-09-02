import io
import tarfile
import tempfile
import unittest
from pathlib import Path

import solution


def add_text(archive, name, text):
    payload = text.encode()
    member = tarfile.TarInfo(name)
    member.size = len(payload)
    archive.addfile(member, io.BytesIO(payload))


class OriginalBenchmarkFunctionalityTests(unittest.TestCase):
    def test_extracts_flat_and_nested_regular_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / "archive.tar"
            with tarfile.open(archive_path, "w") as archive:
                add_text(archive, "a.txt", "a")
                add_text(archive, "dir0/dir1/d.txt", "d")
            destination = root / "dest"
            self.assertTrue(
                solution.extract_tar_to_path(str(archive_path), str(destination))
            )
            self.assertEqual((destination / "a.txt").read_text(), "a")
            self.assertEqual((destination / "dir0/dir1/d.txt").read_text(), "d")
