import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import secrets  # noqa: E402


class TestMask(unittest.TestCase):
    def setUp(self):
        self._saved = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._saved)

    def test_masks_known_api_key_value_embedded_in_url(self):
        os.environ["DUMMY_TEST_API_KEY"] = "sekret1234value"
        url = "https://example.com/api?foo=1&auth=sekret1234value&bar=2"
        masked = secrets.mask(url)
        self.assertNotIn("sekret1234value", masked)
        self.assertIn("***MASKED***", masked)

    def test_masks_known_api_key_value_in_error_string(self):
        os.environ["DUMMY_TEST_API_KEY"] = "abcd9999secret"
        message = "ConnectionError: failed for token abcd9999secret after 4 attempts"
        masked = secrets.mask(message)
        self.assertNotIn("abcd9999secret", masked)

    def test_masks_servicekey_query_param(self):
        text = "GET https://apis.data.go.kr/foo?serviceKey=AbCd1234%2F%3D&numOfRows=10"
        masked = secrets.mask(text)
        self.assertNotIn("AbCd1234", masked)
        self.assertIn("serviceKey=***MASKED***", masked)

    def test_masks_apikey_query_param_case_insensitive(self):
        text = "url with apiKey=zzz999yyy in it"
        masked = secrets.mask(text)
        self.assertNotIn("zzz999yyy", masked)
        self.assertIn("apiKey=***MASKED***", masked)

    def test_masks_key_and_authkey_params(self):
        text = "a?key=one111two&b?authkey=three222four"
        masked = secrets.mask(text)
        self.assertNotIn("one111two", masked)
        self.assertNotIn("three222four", masked)

    def test_short_values_under_len4_not_masked_by_value_pass(self):
        # len < 4 is excluded from the value-based pass per spec, but the
        # param-name regex pass can still catch it if it's in key=... form.
        os.environ["SHORT_API_KEY"] = "ab1"
        text = "no query param form here, just ab1 alone"
        masked = secrets.mask(text)
        # value-based pass should NOT have touched this (len<4 excluded)
        self.assertIn("ab1", masked)

    def test_no_env_keys_set_leaves_text_mostly_intact_except_param_regex(self):
        text = "plain text with no secrets"
        masked = secrets.mask(text)
        self.assertEqual(masked, text)

    def test_check_env_vars_present_never_returns_values(self):
        os.environ["PRESENCE_TEST_API_KEY"] = "somevalue123"
        result = secrets.check_env_vars_present(["PRESENCE_TEST_API_KEY", "NOT_SET_API_KEY"])
        self.assertEqual(result, {"PRESENCE_TEST_API_KEY": True, "NOT_SET_API_KEY": False})
        self.assertNotIn("somevalue123", str(result))

    def test_discover_required_env_vars(self):
        class FakeModule:
            REQUIRED_ENV_VAR = "FAKE_SOURCE_API_KEY"

        registry = {"fake_source": FakeModule}
        indicators = [
            {"id": "a", "source": "fake_source"},
            {"id": "b", "source": "fake_source"},
        ]
        result = secrets.discover_required_env_vars(indicators, registry)
        self.assertEqual(result, {"FAKE_SOURCE_API_KEY"})


if __name__ == "__main__":
    unittest.main()
