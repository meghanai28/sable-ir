import unittest

import solution


class OriginalSecurityTests(unittest.TestCase):
    def test_rejects_private_initial_destination_before_transport(self):
        calls = []

        def transport(url):
            calls.append(url)
            return 200, {}, "internal"

        with self.assertRaises(ValueError):
            solution.fetch_text("http://127.0.0.1/admin", transport, lambda _host: ["127.0.0.1"])
        self.assertEqual(calls, [])

    def test_never_fetches_private_redirect_destination(self):
        calls = []

        def transport(url):
            calls.append(url)
            return 302, {"Location": "http://169.254.169.254/latest"}, ""

        def resolver(hostname):
            if hostname == "public.example":
                return ["93.184.216.34"]
            return ["169.254.169.254"]

        with self.assertRaises(ValueError):
            solution.fetch_text("https://public.example/start", transport, resolver)
        self.assertEqual(calls, ["https://public.example/start"])
