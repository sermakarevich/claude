#!/usr/bin/env bash
# Install the postgres MCP server globally for Claude Code (uv-based).
#
# Copies the project (server.py, pyproject.toml, credentials/) to
# ~/.claude/mcp-servers/postgres/ and registers it with `claude mcp add` at
# user scope. Dependencies are resolved by `uv run` against pyproject.toml.
#
# Existing credential files in the target are preserved (not overwritten).
#
# Requires `uv` (https://docs.astral.sh/uv/) and the `claude` CLI on PATH.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$HOME/.claude/mcp-servers/postgres"

command -v uv     >/dev/null || { echo "Error: 'uv' not found in PATH." >&2; exit 1; }
command -v claude >/dev/null || { echo "Error: 'claude' CLI not found in PATH." >&2; exit 1; }

echo "Installing postgres MCP server"
echo "  source : $SCRIPT_DIR"
echo "  target : $TARGET_DIR"

mkdir -p "$TARGET_DIR"
cp "$SCRIPT_DIR/server.py"      "$TARGET_DIR/server.py"
cp "$SCRIPT_DIR/pyproject.toml" "$TARGET_DIR/pyproject.toml"

mkdir -p "$TARGET_DIR/credentials"
if [ -d "$SCRIPT_DIR/credentials" ]; then
    for cfg in "$SCRIPT_DIR"/credentials/*.json; do
        [ -f "$cfg" ] || continue
        name="$(basename "$cfg")"
        if [ ! -f "$TARGET_DIR/credentials/$name" ]; then
            cp "$cfg" "$TARGET_DIR/credentials/$name"
            echo "  added credentials: $name"
        else
            echo "  kept existing credentials: $name"
        fi
    done
fi

echo "Pre-warming uv environment ..."
(cd "$TARGET_DIR" && uv sync >/dev/null 2>&1) || true

echo "Registering with Claude Code (user scope) ..."
claude mcp remove postgres --scope user >/dev/null 2>&1 || true
claude mcp add postgres --scope user -- \
    uv run --directory "$TARGET_DIR" python server.py

echo
echo "Done. Verify with:  claude mcp list"
