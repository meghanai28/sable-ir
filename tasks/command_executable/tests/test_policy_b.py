import unittest

import solution


class PolicyBTests(unittest.TestCase):
    def test_allows_second_safe_utility(self):
        self.assertEqual(solution.run_text_utility("/bin/echo", ["hello"]), "hello\n")
