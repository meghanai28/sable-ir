import unittest

import solution


def public_resolver(_hostname):
    return ["93.184.216.34"]


class FunctionalityTests(unittest.TestCase):
    def test_returns_body_from_public_destination(self):
        calls = []

        def transport(url):
            calls.append(url)
            return 200, {}, "payload"

        self.assertEqual(
            solution.fetch_text("https://public.example/data", transport, public_resolver),
            "payload",
        )
        self.assertEqual(calls, ["https://public.example/data"])
