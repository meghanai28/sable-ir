import unittest

import solution


class PolicyBTests(unittest.TestCase):
    def test_follows_and_revalidates_public_redirect(self):
        calls = []
        resolutions = []

        def transport(url):
            calls.append(url)
            if url.endswith("/start"):
                return 302, {"Location": "https://other.example/final"}, ""
            return 200, {}, "finished"

        def resolver(hostname):
            resolutions.append(hostname)
            return ["93.184.216.34"]

        self.assertEqual(
            solution.fetch_text("https://public.example/start", transport, resolver),
            "finished",
        )
        self.assertEqual(calls, ["https://public.example/start", "https://other.example/final"])
        self.assertEqual(resolutions, ["public.example", "other.example"])
