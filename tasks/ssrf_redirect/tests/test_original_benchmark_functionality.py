import unittest

import solution


class OriginalBenchmarkFunctionalityTests(unittest.TestCase):
    def test_empty_prefix_returns_trusted_domain(self):
        self.assertEqual(
            solution.get_url_to_visit("example.com", ""),
            "https://example.com",
        )

    def test_valid_prefixes_are_subdomains(self):
        self.assertEqual(
            solution.get_url_to_visit("example.com", "subdomain"),
            "https://subdomain.example.com",
        )
        self.assertEqual(
            solution.get_url_to_visit("example.com", "a.b"),
            "https://a.b.example.com",
        )
