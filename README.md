# Claude Extensions

## Status Line

A custom status line that shows model, context usage, 5h/7d rate limits with reset countdowns, session duration, cost, lines changed, cwd, and git branch.

![Status line](assets/status_line.png)

See [status_line/](status_line/) — run `status_line/install.sh` to install.

## Refs

- [hooks/shortcuts/](hooks/shortcuts/) — turns prompt prefixes like `fix:` and `q:` into background extractions that capture corrections and Q&A into per-repo artifacts.
- [mcp/youtube_transcript/](mcp/youtube_transcript/) — MCP server exposing a tool to fetch YouTube video transcripts by URL or video ID.
