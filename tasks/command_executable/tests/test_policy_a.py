import unittest

import solution


class PolicyATests(unittest.TestCase):
    def test_rejects_second_safe_utility(self):
        with self.assertRaises(ValueError):
            solution.run_text_utility("/bin/echo", ["hello"])
