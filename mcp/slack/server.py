#!/usr/bin/env python3
"""MCP server for sending Slack messages and files as a specific user.

Each workspace identity is a JSON file in `credentials/` next to this script
containing a Slack User OAuth Token (xoxp-...). Messages are posted *as* that
user; file uploads are attributed to that user. String values starting with
`$` are resolved from the environment.

User OAuth scopes typically needed:
    chat:write, files:write, channels:read, groups:read, im:read, mpim:read,
    users:read, users:read.email (optional), reactions:write (optional).
"""

import json
import os
import re
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

CREDENTIALS_DIR = Path(__file__).parent / "credentials"

_ID_RE = re.compile(r"^[CGDUW][A-Z0-9]{8,}$")


def _load_configs() -> dict[str, dict]:
    if not CREDENTIALS_DIR.is_dir():
        return {}
    out: dict[str, dict] = {}
    for path in sorted(CREDENTIALS_DIR.glob("*.json")):
        if path.name.startswith("."):
            continue
        with path.open() as f:
            out[path.stem] = json.load(f)
    return out


_configs = _load_configs()
_names_hint = (
    f"\n\nAvailable workspaces: {', '.join(_configs.keys())}." if _configs else ""
)

mcp = FastMCP(
    "slack",
    instructions=(
        "Send messages and files to Slack as a specific user. Each workspace "
        "identity is defined by a JSON file in the `credentials/` directory "
        "next to this server containing a User OAuth Token (xoxp-...) — "
        "messages posted with that token appear from whoever authorized it. "
        "Tools: `list_workspaces`, `whoami`, `list_channels`, `find_user`, "
        "`send_message`, `upload_file`, `add_reaction`."
        + _names_hint
    ),
)


def _resolve(value: Any) -> Any:
    if isinstance(value, str) and value.startswith("$"):
        return os.environ.get(value[1:], "")
    return value


def _client(workspace: str) -> WebClient:
    if workspace not in _configs:
        available = ", ".join(_configs.keys()) or "(none)"
        raise ValueError(f"Unknown workspace '{workspace}'. Available: {available}")
    cfg = _configs[workspace]
    token = _resolve(cfg.get("token", ""))
    if not token:
        raise ValueError(f"workspace '{workspace}' has empty token")
    if not token.startswith(("xoxp-", "xoxe.xoxp-")):
        # Bot/app tokens still work for some endpoints but won't post 'as user'.
        # Warn via exception text on lookup, but allow the call to proceed.
        pass
    return WebClient(token=token)


def _err(message: str, **extra: Any) -> dict[str, Any]:
    out: dict[str, Any] = {"ok": False, "error": message}
    out.update(extra)
    return out


def _resolve_channel(client: WebClient, channel: str) -> str:
    """Resolve a channel reference to a conversation ID.

    Accepts: raw IDs (C..., G..., D..., U..., W...), "#channel-name",
    "@username", a bare channel/user name, or an email address (for DMs).
    User refs are converted into a DM channel via `conversations.open`.
    """
    if not channel:
        raise ValueError("channel is empty")

    ref = channel.strip()

    if _ID_RE.match(ref):
        if ref.startswith(("U", "W")):
            dm = client.conversations_open(users=ref)
            return dm["channel"]["id"]
        return ref

    name = ref.lstrip("#@")

    cursor: str | None = None
    while True:
        resp = client.conversations_list(
            cursor=cursor,
            limit=200,
            types="public_channel,private_channel,mpim",
            exclude_archived=True,
        )
        for ch in resp.get("channels", []):
            if ch.get("name") == name:
                return ch["id"]
        cursor = resp.get("response_metadata", {}).get("next_cursor") or None
        if not cursor:
            break

    user_id: str | None = None
    if "@" in name and "." in name:
        try:
            resp = client.users_lookupByEmail(email=name)
            user_id = resp["user"]["id"]
        except SlackApiError:
            user_id = None

    if not user_id:
        cursor = None
        while True:
            resp = client.users_list(cursor=cursor, limit=200)
            for u in resp.get("members", []):
                if u.get("deleted"):
                    continue
                profile = u.get("profile") or {}
                if name in (
                    u.get("name"),
                    profile.get("display_name"),
                    profile.get("display_name_normalized"),
                    profile.get("real_name"),
                ):
                    user_id = u["id"]
                    break
            if user_id:
                break
            cursor = resp.get("response_metadata", {}).get("next_cursor") or None
            if not cursor:
                break

    if user_id:
        dm = client.conversations_open(users=user_id)
        return dm["channel"]["id"]

    raise ValueError(f"could not resolve channel/user reference '{channel}'")


@mcp.tool()
def list_workspaces() -> list[str]:
    """List configured Slack workspace identity names."""
    return list(_configs.keys())


@mcp.tool()
def whoami(workspace: str) -> dict:
    """Show the user identity attached to the workspace's token.

    Args:
        workspace: Workspace name (from `list_workspaces`).

    Returns:
        {ok, user_id, user_name, team, team_id, url} on success.
    """
    try:
        resp = _client(workspace).auth_test()
    except (SlackApiError, ValueError) as e:
        return _err(str(e))
    return {
        "ok": True,
        "user_id": resp.get("user_id"),
        "user_name": resp.get("user"),
        "team_id": resp.get("team_id"),
        "team": resp.get("team"),
        "url": resp.get("url"),
        "is_bot_token": str(resp.get("user", "")).lower() in ("", "bot"),
    }


@mcp.tool()
def list_channels(
    workspace: str,
    types: str = "public_channel,private_channel",
    limit: int = 200,
    name_contains: str | None = None,
) -> list[dict]:
    """List channels in the workspace (one page).

    Args:
        workspace: Workspace name.
        types: Comma-separated channel types. Allowed values:
            `public_channel`, `private_channel`, `mpim`, `im`.
        limit: Max channels per page. Default: 200.
        name_contains: Optional case-insensitive substring filter on channel name.

    Returns:
        List of {id, name, is_private, is_member, num_members}.
    """
    try:
        resp = _client(workspace).conversations_list(
            types=types, limit=limit, exclude_archived=True
        )
    except (SlackApiError, ValueError) as e:
        return [_err(str(e))]
    needle = name_contains.lower() if name_contains else None
    out = []
    for c in resp.get("channels", []):
        if needle and needle not in (c.get("name") or "").lower():
            continue
        out.append(
            {
                "id": c["id"],
                "name": c.get("name") or c.get("user"),
                "is_private": c.get("is_private", False),
                "is_member": c.get("is_member", False),
                "num_members": c.get("num_members"),
            }
        )
    return out


@mcp.tool()
def find_user(workspace: str, query: str) -> list[dict]:
    """Find users by substring match on name, display name, real name, or email.

    Args:
        workspace: Workspace name.
        query: Substring to search for. Case-insensitive. Leading `@` is stripped.

    Returns:
        List of {id, name, real_name, display_name, email}. Bots and deleted
        users are excluded.
    """
    try:
        client = _client(workspace)
    except ValueError as e:
        return [_err(str(e))]

    q = query.lower().lstrip("@")
    results: list[dict] = []
    cursor: str | None = None
    try:
        while True:
            resp = client.users_list(cursor=cursor, limit=200)
            for u in resp.get("members", []):
                if u.get("deleted") or u.get("is_bot"):
                    continue
                profile = u.get("profile") or {}
                haystack = " ".join(
                    [
                        u.get("name") or "",
                        u.get("real_name") or "",
                        profile.get("display_name") or "",
                        profile.get("email") or "",
                    ]
                ).lower()
                if q in haystack:
                    results.append(
                        {
                            "id": u["id"],
                            "name": u.get("name"),
                            "real_name": u.get("real_name"),
                            "display_name": profile.get("display_name"),
                            "email": profile.get("email"),
                        }
                    )
            cursor = resp.get("response_metadata", {}).get("next_cursor") or None
            if not cursor:
                break
    except SlackApiError as e:
        return [_err(str(e))]
    return results


@mcp.tool()
def send_message(
    workspace: str,
    channel: str,
    text: str,
    thread_ts: str | None = None,
    blocks: list[dict] | None = None,
    reply_broadcast: bool = False,
    unfurl_links: bool | None = None,
    unfurl_media: bool | None = None,
) -> dict:
    """Post a message to a channel or DM, as the workspace's authorized user.

    Args:
        workspace: Workspace name.
        channel: Channel ID (C/G/D...), `#channel-name`, `@username`, bare
            channel/user name, or email (DM). Names are resolved against the
            workspace; prefer IDs for speed.
        text: Message text in Slack mrkdwn. Used as fallback when `blocks` is set
            and as the notification preview.
        thread_ts: Parent message `ts` to reply inside a thread (optional).
        blocks: Block Kit blocks for rich formatting (optional). See
            https://api.slack.com/block-kit.
        reply_broadcast: When replying in a thread, also post to the channel.
        unfurl_links / unfurl_media: Override link/media unfurl behavior.

    Returns:
        {ok, channel, ts, permalink} on success, {ok: false, error} on failure.
    """
    try:
        client = _client(workspace)
        ch = _resolve_channel(client, channel)
    except (SlackApiError, ValueError) as e:
        return _err(str(e))

    kwargs: dict[str, Any] = {"channel": ch, "text": text}
    if thread_ts:
        kwargs["thread_ts"] = thread_ts
        if reply_broadcast:
            kwargs["reply_broadcast"] = True
    if blocks:
        kwargs["blocks"] = blocks
    if unfurl_links is not None:
        kwargs["unfurl_links"] = unfurl_links
    if unfurl_media is not None:
        kwargs["unfurl_media"] = unfurl_media

    try:
        resp = client.chat_postMessage(**kwargs)
    except SlackApiError as e:
        return _err(str(e))

    permalink = None
    try:
        pl = client.chat_getPermalink(channel=resp["channel"], message_ts=resp["ts"])
        permalink = pl.get("permalink")
    except SlackApiError:
        pass

    return {
        "ok": True,
        "channel": resp["channel"],
        "ts": resp["ts"],
        "permalink": permalink,
    }


@mcp.tool()
def upload_file(
    workspace: str,
    channel: str,
    file_path: str,
    title: str | None = None,
    initial_comment: str | None = None,
    thread_ts: str | None = None,
    filename: str | None = None,
) -> dict:
    """Upload a local file to a Slack channel or DM as the authorized user.

    Uses the modern `files.uploadV2` flow. The file is read from disk on the
    machine running this server.

    Args:
        workspace: Workspace name.
        channel: Channel ID, `#channel-name`, `@username`, or email (DM).
        file_path: Absolute or `~`-relative path to the local file.
        title: Display title in Slack. Defaults to the file's basename.
        initial_comment: Optional message text posted with the file.
        thread_ts: Optional thread parent `ts` to attach the upload to.
        filename: Override the uploaded filename (defaults to basename of file_path).

    Returns:
        {ok, file_id, permalink, title, size} on success.
    """
    try:
        client = _client(workspace)
        ch = _resolve_channel(client, channel)
    except (SlackApiError, ValueError) as e:
        return _err(str(e))

    path = Path(file_path).expanduser()
    if not path.is_file():
        return _err(f"file not found: {path}")

    kwargs: dict[str, Any] = {
        "channel": ch,
        "file": str(path),
        "filename": filename or path.name,
    }
    if title:
        kwargs["title"] = title
    if initial_comment:
        kwargs["initial_comment"] = initial_comment
    if thread_ts:
        kwargs["thread_ts"] = thread_ts

    try:
        resp = client.files_upload_v2(**kwargs)
    except SlackApiError as e:
        return _err(str(e))

    file_info = resp.get("file")
    if not file_info:
        files = resp.get("files") or []
        file_info = files[0] if files else {}

    return {
        "ok": True,
        "file_id": file_info.get("id"),
        "permalink": file_info.get("permalink"),
        "title": file_info.get("title"),
        "size": file_info.get("size"),
    }


@mcp.tool()
def add_reaction(
    workspace: str, channel: str, timestamp: str, emoji: str
) -> dict:
    """Add an emoji reaction to a message.

    Args:
        workspace: Workspace name.
        channel: Channel ID or name where the message lives.
        timestamp: The message `ts` (returned by `send_message`).
        emoji: Emoji name without surrounding colons (e.g. `thumbsup`, `rocket`).
    """
    try:
        client = _client(workspace)
        ch = _resolve_channel(client, channel)
        client.reactions_add(channel=ch, timestamp=timestamp, name=emoji.strip(":"))
    except (SlackApiError, ValueError) as e:
        return _err(str(e))
    return {"ok": True}


if __name__ == "__main__":
    mcp.run()
