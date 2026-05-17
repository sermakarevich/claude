#!/usr/bin/env bash
# Install the youtube_transcript MCP server globally for Claude Code (uv-based).
#
# Copies server.py to ~/.claude/mcp-servers/youtube_transcript/ and registers
# it with `claude mcp add` at user scope. Dependencies are declared inline
# (PEP 723) in server.py and resolved by `uv run --script` at runtime.
#
# Requires `uv` (https://docs.astral.sh/uv/) and the `claude` CLI on PATH.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$HOME/.claude/mcp-servers/youtube_transcript"

command -v uv     >/dev/null || { echo "Error: 'uv' not found in PATH." >&2; exit 1; }
command -v claude >/dev/null || { echo "Error: 'claude' CLI not found in PATH." >&2; exit 1; }

echo "Installing youtube_transcript MCP server"
echo "  source : $SCRIPT_DIR"
echo "  target : $TARGET_DIR"

mkdir -p "$TARGET_DIR"
cp "$SCRIPT_DIR/server.py" "$TARGET_DIR/server.py"

# Mirror the instructions/ folder so `workflow://<name>` resources resolve.
rm -rf "$TARGET_DIR/instructions"
if [ -d "$SCRIPT_DIR/instructions" ]; then
    cp -R "$SCRIPT_DIR/instructions" "$TARGET_DIR/instructions"
fi

echo "Pre-warming uv cache ..."
uv sync --script "$TARGET_DIR/server.py" >/dev/null 2>&1 || true

# Remove any prior venv-based install
rm -rf "$HOME/.claude/mcp_servers/youtube_transcript"

echo "Registering with Claude Code (user scope) ..."
claude mcp remove youtube_transcript --scope user >/dev/null 2>&1 || true
claude mcp add youtube_transcript --scope user -- \
    uv run --script "$TARGET_DIR/server.py"

echo
echo "Done. Verify with:  claude mcp list"
