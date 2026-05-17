# Futurum Equities → Signals

For a list of Futurum Equities YouTube videos:

1. Spawn one general-purpose agent per video, in parallel.
2. Each agent calls `mcp__youtube_transcript__get_transcript(video=<bare-id>)` and extracts useful and meaningfull information about stocks and market. Highlight extreme cases. 
3. Aggregate findings → save as `mcp/youtube_transcript/outputs/{DATE}_report_{SHORT_NAME}.md` (DATE = YYYY-MM-DD) with cross-video tally (B=Buy, S=Sell, O=Owned mention counts) + per-video sections.

Notes:
- Pass bare 11-char video IDs (MCP doesn't parse `/live/` URLs).
- Agents must load the tool schema first: `ToolSearch select:mcp__youtube_transcript__get_transcript`.
- Watch for ticker mishearings: NBIS (not NVTS), WULF (not TWLF), AEHR (not EEHR), LITE vs LSCC.
