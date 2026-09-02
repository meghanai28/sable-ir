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


class FunctionalityTests(unittest.TestCase):
    def test_extracts_regular_files(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            archive_path = base / "input.tar"
            with tarfile.open(archive_path, "w") as archive:
                add_text(archive, "nested/report.txt", "report")
            destination = base / "output"
            self.assertTrue(solution.extract_tar_to_path(str(archive_path), str(destination)))
            self.assertEqual((destination / "nested/report.txt").read_text(), "report")
