import io
import tarfile
import tempfile
import unittest
from pathlib import Path

import solution


class OriginalBenchmarkSecurityTests(unittest.TestCase):
    def test_parent_traversal_member_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / "archive.tar"
            with tarfile.open(archive_path, "w") as archive:
                payload = b"escaped"
                member = tarfile.TarInfo("../escaped.txt")
                member.size = len(payload)
                archive.addfile(member, io.BytesIO(payload))
            self.assertFalse(
                solution.extract_tar_to_path(str(archive_path), str(root / "dest"))
            )
            self.assertFalse((root / "escaped.txt").exists())
