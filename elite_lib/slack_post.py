"""Slack bot-token posting helper (stdlib only, no extra dependency).

Used by daily_summary to auto-post the morning report headline to Slack.
Token resolution mirrors elite_lib.bigquery.get_client(): an env var takes
priority over a gitignored local override file, so no secret is ever
committed to git.
"""

from __future__ import annotations

import json
import mimetypes
import os
import uuid
import urllib.error
import urllib.request
from pathlib import Path

SLACK_POST_MESSAGE_URL = "https://slack.com/api/chat.postMessage"
SLACK_DELETE_MESSAGE_URL = "https://slack.com/api/chat.delete"
SLACK_CONVERSATIONS_HISTORY_URL = "https://slack.com/api/conversations.history"
SLACK_CONVERSATIONS_OPEN_URL = "https://slack.com/api/conversations.open"
SLACK_FILES_UPLOAD_URL = "https://slack.com/api/files.upload"


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
    username: str | None = None,
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

    payload: dict[str, str] = {"channel": channel, "text": text}
    if username:
        payload["username"] = username
    body_bytes = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        SLACK_POST_MESSAGE_URL,
        data=body_bytes,
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


def delete_message(
    channel: str,
    ts: str,
    *,
    token: str | None = None,
    timeout: float = 15.0,
) -> dict:
    """Delete a message the bot posted (chat.delete)."""
    bot_token = token or resolve_token()
    if not bot_token:
        raise SlackPostError(
            "No Slack bot token configured. Set SLACK_BOT_TOKEN or "
            "elite_lib/_local_credentials.py before deleting messages."
        )
    if not channel or not ts:
        raise SlackPostError("delete_message requires channel and ts")
    return _slack_json_api(
        SLACK_DELETE_MESSAGE_URL,
        {"channel": channel, "ts": ts},
        token=bot_token,
        timeout=timeout,
    )


def find_channel_messages(
    channel: str,
    *,
    token: str | None = None,
    limit: int = 50,
    timeout: float = 15.0,
) -> list[dict]:
    """Recent messages in a channel (requires channels:history on the bot)."""
    bot_token = token or resolve_token()
    if not bot_token:
        raise SlackPostError(
            "No Slack bot token configured. Set SLACK_BOT_TOKEN or "
            "elite_lib/_local_credentials.py before reading channel history."
        )
    body = _slack_json_api(
        SLACK_CONVERSATIONS_HISTORY_URL,
        {"channel": channel, "limit": limit},
        token=bot_token,
        timeout=timeout,
    )
    return list(body.get("messages") or [])


def _slack_json_api(
    url: str,
    payload: dict,
    *,
    token: str,
    timeout: float = 15.0,
) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
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


def open_dm(user_id: str, *, token: str | None = None, timeout: float = 15.0) -> str:
    """Open (or reuse) a DM channel with a Slack user id; return channel id."""
    bot_token = token or resolve_token()
    if not bot_token:
        raise SlackPostError(
            "No Slack bot token configured. Set SLACK_BOT_TOKEN or "
            "elite_lib/_local_credentials.py before uploading files."
        )
    if not user_id:
        raise SlackPostError("open_dm requires a non-empty user id")
    body = _slack_json_api(
        SLACK_CONVERSATIONS_OPEN_URL,
        {"users": user_id},
        token=bot_token,
        timeout=timeout,
    )
    channel = (body.get("channel") or {}).get("id")
    if not channel:
        raise SlackPostError("conversations.open returned no channel id")
    return channel


def upload_file(
    file_path: Path | str,
    channel_id: str,
    *,
    comment: str = "",
    title: str = "",
    token: str | None = None,
    timeout: float = 120.0,
) -> dict:
    """Upload a file to a Slack channel or DM via files.upload."""
    bot_token = token or resolve_token()
    if not bot_token:
        raise SlackPostError(
            "No Slack bot token configured. Set SLACK_BOT_TOKEN or "
            "elite_lib/_local_credentials.py before uploading files."
        )
    path = Path(file_path)
    if not path.is_file():
        raise SlackPostError(f"Upload file not found: {path}")
    if not channel_id:
        raise SlackPostError("upload_file requires a non-empty channel id")

    boundary = f"----EliteBoundary{uuid.uuid4().hex}"
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    fields = {
        "channels": channel_id,
        "filename": path.name,
        "title": title or path.name,
    }
    if comment:
        fields["initial_comment"] = comment

    body = bytearray()
    for key, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"))
        body.extend(f"{value}\r\n".encode("utf-8"))
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(
        f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'.encode(
            "utf-8"
        )
    )
    body.extend(f"Content-Type: {mime}\r\n\r\n".encode("utf-8"))
    body.extend(path.read_bytes())
    body.extend(f"\r\n--{boundary}--\r\n".encode("utf-8"))

    request = urllib.request.Request(
        SLACK_FILES_UPLOAD_URL,
        data=bytes(body),
        method="POST",
        headers={
            "Authorization": f"Bearer {bot_token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise SlackPostError(f"Slack upload failed: {exc}") from exc
    if not result.get("ok"):
        raise SlackPostError(f"Slack API error: {result.get('error', 'unknown_error')}")
    return result
