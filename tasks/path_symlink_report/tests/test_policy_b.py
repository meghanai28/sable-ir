import tempfile
import unittest
from pathlib import Path

import solution


class PolicyBTests(unittest.TestCase):
    def test_allows_link_whose_resolved_target_is_inside_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "actual.txt").write_text("contained", encoding="utf-8")
            (root / "alias.txt").symlink_to("actual.txt")
            self.assertEqual(solution.read_report("alias.txt", str(root)), "contained")

    def test_allows_contained_symlink_in_an_intermediate_component(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "actual").mkdir()
            (root / "actual" / "report.txt").write_text("contained", encoding="utf-8")
            (root / "alias").symlink_to("actual", target_is_directory=True)
            self.assertEqual(
                solution.read_report("alias/report.txt", str(root)),
                "contained",
            )
