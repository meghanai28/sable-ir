import unittest

import solution


class PolicyATests(unittest.TestCase):
    def test_rejects_redirect_to_public_destination(self):
        calls = []

        def transport(url):
            calls.append(url)
            return 302, {"Location": "https://other.example/final"}, ""

        def resolver(_hostname):
            return ["93.184.216.34"]

        with self.assertRaises(ValueError):
            solution.fetch_text("https://public.example/start", transport, resolver)
        self.assertEqual(calls, ["https://public.example/start"])
