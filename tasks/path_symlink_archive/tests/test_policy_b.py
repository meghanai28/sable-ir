import io
import tarfile
import tempfile
import unittest
from pathlib import Path

import solution


class PolicyBTests(unittest.TestCase):
    def test_extracts_contained_symbolic_link_member(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            archive_path = base / "input.tar"
            with tarfile.open(archive_path, "w") as archive:
                payload = b"inside"
                target = tarfile.TarInfo("target.txt")
                target.size = len(payload)
                archive.addfile(target, io.BytesIO(payload))
                link = tarfile.TarInfo("alias.txt")
                link.type = tarfile.SYMTYPE
                link.linkname = "target.txt"
                archive.addfile(link)
            destination = base / "out"
            self.assertTrue(solution.extract_tar_to_path(str(archive_path), str(destination)))
            self.assertEqual((destination / "alias.txt").read_text(), "inside")

    def test_extracts_contained_hard_link_member(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            archive_path = base / "input.tar"
            with tarfile.open(archive_path, "w") as archive:
                payload = b"inside"
                target = tarfile.TarInfo("target.txt")
                target.size = len(payload)
                archive.addfile(target, io.BytesIO(payload))
                link = tarfile.TarInfo("alias.txt")
                link.type = tarfile.LNKTYPE
                link.linkname = "target.txt"
                archive.addfile(link)
            destination = base / "out"
            self.assertTrue(solution.extract_tar_to_path(str(archive_path), str(destination)))
            self.assertEqual((destination / "alias.txt").read_text(), "inside")
