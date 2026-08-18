"""Unit tests for elite_lib.slack_post — no live Slack calls.

urllib.request.urlopen is mocked throughout, so these tests never hit the
network and never require a real bot token.
"""

from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch

from elite_lib.slack_post import SlackPostError, post_message, resolve_token


class ResolveTokenTests(unittest.TestCase):
    def test_env_var_takes_priority(self) -> None:
        with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-env"}, clear=False):
            self.assertEqual(resolve_token(), "xoxb-env")

    def test_falls_back_to_none_when_unset_and_no_local_override(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with patch("elite_lib.slack_post._local_default_token", return_value=None):
                self.assertIsNone(resolve_token())

    def test_falls_back_to_local_override_file(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with patch("elite_lib.slack_post._local_default_token", return_value="xoxb-local"):
                self.assertEqual(resolve_token(), "xoxb-local")


class PostMessageTests(unittest.TestCase):
    def test_raises_without_a_token(self) -> None:
        with patch("elite_lib.slack_post.resolve_token", return_value=None):
            with self.assertRaises(SlackPostError):
                post_message("C123", "hello")

    def test_raises_without_a_channel(self) -> None:
        with self.assertRaises(SlackPostError):
            post_message("", "hello", token="xoxb-test")

    def test_success_calls_slack_api_with_bearer_token(self) -> None:
        response = MagicMock()
        response.read.return_value = json.dumps({"ok": True, "ts": "123.456"}).encode("utf-8")
        response.__enter__.return_value = response

        with patch("elite_lib.slack_post.urllib.request.urlopen", return_value=response) as mock_open:
            result = post_message("C123", "hello", token="xoxb-test")

        self.assertEqual(result["ok"], True)
        request = mock_open.call_args[0][0]
        self.assertEqual(request.headers["Authorization"], "Bearer xoxb-test")
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(body, {"channel": "C123", "text": "hello"})

    def test_raises_when_slack_returns_not_ok(self) -> None:
        response = MagicMock()
        response.read.return_value = json.dumps(
            {"ok": False, "error": "channel_not_found"}
        ).encode("utf-8")
        response.__enter__.return_value = response

        with patch("elite_lib.slack_post.urllib.request.urlopen", return_value=response):
            with self.assertRaises(SlackPostError) as ctx:
                post_message("Cbad", "hello", token="xoxb-test")
        self.assertIn("channel_not_found", str(ctx.exception))

    def test_wraps_network_errors(self) -> None:
        import urllib.error

        with patch(
            "elite_lib.slack_post.urllib.request.urlopen",
            side_effect=urllib.error.URLError("boom"),
        ):
            with self.assertRaises(SlackPostError):
                post_message("C123", "hello", token="xoxb-test")


if __name__ == "__main__":
    unittest.main()
