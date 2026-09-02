import io
import tarfile
import tempfile
import unittest
from pathlib import Path

import solution


class OriginalSecurityTests(unittest.TestCase):
    def test_rejects_parent_traversal_member(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            archive_path = base / "input.tar"
            with tarfile.open(archive_path, "w") as archive:
                payload = b"escaped"
                member = tarfile.TarInfo("../escape.txt")
                member.size = len(payload)
                archive.addfile(member, io.BytesIO(payload))
            self.assertFalse(solution.extract_tar_to_path(str(archive_path), str(base / "out")))
            self.assertFalse((base / "escape.txt").exists())

    def test_rejects_link_to_outside_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            archive_path = base / "input.tar"
            with tarfile.open(archive_path, "w") as archive:
                link = tarfile.TarInfo("escape")
                link.type = tarfile.SYMTYPE
                link.linkname = "../../outside.txt"
                archive.addfile(link)
            self.assertFalse(solution.extract_tar_to_path(str(archive_path), str(base / "out")))
            self.assertFalse((base / "outside.txt").exists())
