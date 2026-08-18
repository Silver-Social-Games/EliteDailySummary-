"""Slack bot-token posting helper (stdlib only, no extra dependency).

Used by daily_summary to auto-post the morning report headline to Slack.
Token resolution mirrors elite_lib.bigquery.get_client(): an env var takes
priority over a gitignored local override file, so no secret is ever
committed to git.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
import os

SLACK_POST_MESSAGE_URL = "https://slack.com/api/chat.postMessage"


class SlackPostError(RuntimeError):
    """Raised when a Slack API call is misconfigured or Slack returns ok=false."""


def _local_default_token() -> str | None:
    """Optional machine-local bot token — never committed to git.

    To avoid setting SLACK_BOT_TOKEN as an env var every session, add to
    elite_lib/_local_credentials.py (gitignored):

        SLACK_BOT_TOKEN = "xoxb-..."
    """
    try:
        from elite_lib._local_credentials import SLACK_BOT_TOKEN  # type: ignore
    except ImportError:
        return None
    return SLACK_BOT_TOKEN or None


def resolve_token() -> str | None:
    """SLACK_BOT_TOKEN env var takes priority over the local override file."""
    return os.environ.get("SLACK_BOT_TOKEN") or _local_default_token()


def post_message(
    channel: str,
    text: str,
    *,
    token: str | None = None,
    timeout: float = 15.0,
) -> dict:
    """Post a message to a Slack channel via chat.postMessage.

    Raises SlackPostError if no token is configured or Slack responds with
    ok=false (e.g. bot not invited to the channel, invalid channel id).
    Scheduled callers should catch this and log/skip rather than fail the
    whole report run over a Slack outage or a missing token.
    """
    bot_token = token or resolve_token()
    if not bot_token:
        raise SlackPostError(
            "No Slack bot token configured. Set the SLACK_BOT_TOKEN environment "
            "variable, or add SLACK_BOT_TOKEN to elite_lib/_local_credentials.py."
        )
    if not channel:
        raise SlackPostError("post_message requires a non-empty channel id")

    payload = json.dumps({"channel": channel, "text": text}).encode("utf-8")
    request = urllib.request.Request(
        SLACK_POST_MESSAGE_URL,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {bot_token}",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise SlackPostError(f"Slack request failed: {exc}") from exc

    if not body.get("ok"):
        raise SlackPostError(f"Slack API error: {body.get('error', 'unknown_error')}")
    return body
