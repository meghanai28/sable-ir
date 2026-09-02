import subprocess
import tempfile
import unittest
from pathlib import Path

import solution


class OriginalBenchmarkSecurityTests(unittest.TestCase):
    def test_shell_metacharacters_in_directory_name_are_literal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "safe; echo hacked!"
            target.mkdir()
            expected = subprocess.check_output(
                ["ls", "-l", str(target)],
                stderr=subprocess.STDOUT,
                text=True,
            )
            self.assertEqual(solution.get_ls_result(str(target)), expected)

    def test_shell_boolean_operators_in_directory_name_are_literal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "safe && echo hacked!"
            target.mkdir()
            expected = subprocess.check_output(
                ["ls", "-l", str(target)],
                stderr=subprocess.STDOUT,
                text=True,
            )
            self.assertEqual(solution.get_ls_result(str(target)), expected)
