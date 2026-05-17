#!/usr/bin/env bash
# Install the claude_code MCP server globally (uv-based).
#
# Copies server.py to ~/.claude/mcp-servers/claude_code/ and registers it
# with `claude mcp add` at user scope so Claude Code itself can consume it.
# The same installed path can be referenced from other MCP clients (e.g.
# hermes' `mcp_servers:` block in ~/.hermes/cli-config.yaml).
#
# Dependencies are declared inline (PEP 723) in server.py and resolved by
# `uv run --script` at runtime.
#
# Requires `uv` (https://docs.astral.sh/uv/) and the `claude` CLI on PATH.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$HOME/.claude/mcp-servers/claude_code"

command -v uv     >/dev/null || { echo "Error: 'uv' not found in PATH." >&2; exit 1; }
command -v claude >/dev/null || { echo "Error: 'claude' CLI not found in PATH." >&2; exit 1; }

echo "Installing claude_code MCP server"
echo "  source : $SCRIPT_DIR"
echo "  target : $TARGET_DIR"

mkdir -p "$TARGET_DIR"
cp "$SCRIPT_DIR/server.py" "$TARGET_DIR/server.py"

echo "Pre-warming uv cache ..."
uv sync --script "$TARGET_DIR/server.py" >/dev/null 2>&1 || true

echo "Registering with Claude Code (user scope) ..."
claude mcp remove claude_code --scope user >/dev/null 2>&1 || true
claude mcp add claude_code --scope user -- \
    uv run --script "$TARGET_DIR/server.py"

echo
echo "Done. Verify with:  claude mcp list"
echo
echo "To wire into hermes, add to ~/.hermes/cli-config.yaml:"
echo
echo "  mcp_servers:"
echo "    claude_code:"
echo "      command: uv"
echo "      args: [\"run\", \"--script\", \"$TARGET_DIR/server.py\"]"
