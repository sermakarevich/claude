# Claude Extensions

## Status Line

A custom status line that shows model, context usage, 5h/7d rate limits with reset countdowns, session duration, cost, lines changed, cwd, and git branch.

![Status line](assets/status_line.png)

See [status_line/](status_line/) — run `status_line/install.sh` to install.

## Refs

- [hooks/shortcuts/](hooks/shortcuts/) — quickly register prompt prefixes (e.g. `fix:`, `q:`) that fire a custom Python callable on any Claude Code hook event. The callable can inject extra context into the current turn, fork a background `claude -p` session, write to per-repo or global artifact files, capture the model's reply from the transcript, or run any other side-effect.
- [mcp/youtube_transcript/](mcp/youtube_transcript/) — MCP server exposing a tool to fetch YouTube video transcripts by URL or video ID.
- [mcp/claude_code/](mcp/claude_code/) — MCP server exposing Claude Code as a delegated-agent tool. Wraps `claude -p` so a third-party MCP-speaking agent (e.g. hermes, or a local Ollama-backed agent) can route work to Claude Code through your existing Claude subscription instead of burning its own API credits or hitting the capability ceiling of a small local model. Returns the final reply plus session metadata for multi-turn continuation.
- [mcp/ask_human/](mcp/ask_human/) — MCP server exposing an `ask_human_question` tool that lets headless subagents and Workflow agents (which can't use `AskUserQuestion`) block until a human answers from a separate operator console. Questions flow through a shared SQLite queue, answered from an auto-refreshing CLI or a web dashboard.
- [mcp/postgres/](mcp/postgres/) — MCP server exposing read-only query tools (`list_schemas`, `list_tables`, `describe_table`, `execute_query`) over one or more named PostgreSQL databases, each defined by a JSON credentials file (`read_only` defaults on).
- [mcp/slack/](mcp/slack/) — MCP server for acting in Slack as a specific user: `send_message`, `upload_file`, and `add_reaction` to a channel, `@user`, or email DM, plus `list_channels`/`find_user` lookups. Each workspace identity is a JSON credentials file.
- [usage_pattern/](usage_pattern/) — drop-in working conventions for repos. Three patterns: `task_loop` (TODO/DONE queue), `artifacts_store` (materialize outputs as markdown + INDEX), `artifacts_loop` (both combined).
