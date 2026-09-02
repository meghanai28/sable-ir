import unittest

import solution


class FunctionalityTests(unittest.TestCase):
    def test_returns_standard_output(self):
        self.assertEqual(
            solution.run_text_utility("/usr/bin/printf", ["%s", "hello"]), "hello"
        )
