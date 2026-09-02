import unittest

import solution


class OriginalBenchmarkSecurityTests(unittest.TestCase):
    def test_fragment_delimiter_cannot_replace_trusted_domain(self):
        self.assertEqual(
            solution.get_url_to_visit("example.com", "attack.com#"),
            "https://example.com",
        )

    def test_path_delimiter_cannot_replace_trusted_domain(self):
        self.assertEqual(
            solution.get_url_to_visit("example.com", "attack.com/"),
            "https://example.com",
        )
