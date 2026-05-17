# Claude Extensions

## Status Line

A custom status line that shows model, context usage, 5h/7d rate limits with reset countdowns, session duration, cost, lines changed, cwd, and git branch.

![Status line](assets/status_line.png)

See [status_line/](status_line/) — run `status_line/install.sh` to install.

## Refs

- [hooks/shortcuts/](hooks/shortcuts/) — quickly register prompt prefixes (e.g. `fix:`, `q:`) that fire a custom Python callable on any Claude Code hook event. The callable can inject extra context into the current turn, fork a background `claude -p` session, write to per-repo or global artifact files, capture the model's reply from the transcript, or run any other side-effect.
- [mcp/youtube_transcript/](mcp/youtube_transcript/) — MCP server exposing a tool to fetch YouTube video transcripts by URL or video ID.
- [mcp/claude_code/](mcp/claude_code/) — MCP server exposing Claude Code itself as a delegated-agent tool. Wraps `claude -p`; lets another MCP client (e.g. a different agent like hermes) hand Claude a prompt and get back the final reply plus session metadata for multi-turn continuation.
- [usage_pattern/](usage_pattern/) — drop-in working conventions for repos. Three patterns: `task_loop` (TODO/DONE queue), `artifacts_store` (materialize outputs as markdown + INDEX), `artifacts_loop` (both combined).
