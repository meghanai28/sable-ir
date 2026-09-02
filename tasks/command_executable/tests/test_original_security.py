import tempfile
import unittest
from pathlib import Path

import solution


class OriginalSecurityTests(unittest.TestCase):
    def test_rejects_command_text_as_executable(self):
        with self.assertRaises(ValueError):
            solution.run_text_utility("/usr/bin/printf; /bin/echo pwned", ["hello"])

    def test_argument_metacharacters_are_literal(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "marker"
            payload = f"safe; /usr/bin/touch {marker}"
            self.assertEqual(
                solution.run_text_utility("/usr/bin/printf", ["%s", payload]), payload
            )
            self.assertFalse(marker.exists())
