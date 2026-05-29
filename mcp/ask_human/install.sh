#!/usr/bin/env bash
# Install the ask_human MCP server + the `agent-chat` operator console (uv-based).
#
#   1. Copies the project to ~/.claude/mcp-servers/ask_human/ and registers the
#      MCP server with `claude mcp add` at user scope.
#   2. Installs the `agent-chat` operator console onto your PATH via `uv tool`.
#
# Both share the same SQLite DB, so it doesn't matter where each one runs.
# Requires `uv` (https://docs.astral.sh/uv/) and the `claude` CLI on PATH.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$HOME/.claude/mcp-servers/ask_human"

command -v uv     >/dev/null || { echo "Error: 'uv' not found in PATH." >&2; exit 1; }
command -v claude >/dev/null || { echo "Error: 'claude' CLI not found in PATH." >&2; exit 1; }

echo "Installing ask_human MCP server"
echo "  source : $SCRIPT_DIR"
echo "  target : $TARGET_DIR"

rm -rf "$TARGET_DIR"
mkdir -p "$TARGET_DIR/src"
cp -R "$SCRIPT_DIR/src/agent_chat" "$TARGET_DIR/src/agent_chat"
cp "$SCRIPT_DIR/pyproject.toml" "$TARGET_DIR/pyproject.toml"
cp "$SCRIPT_DIR/README.md" "$TARGET_DIR/README.md"
find "$TARGET_DIR" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true

echo "Pre-warming uv environment ..."
(cd "$TARGET_DIR" && uv sync >/dev/null 2>&1) || true

echo "Registering MCP server with Claude Code (user scope) ..."
claude mcp remove ask_human --scope user >/dev/null 2>&1 || true
claude mcp add ask_human --scope user -- \
    uv run --directory "$TARGET_DIR" python -m agent_chat.server

echo "Installing the 'agent-chat' operator console onto your PATH ..."
uv tool install --force "$TARGET_DIR"

cat <<EOF

Done. Verify with:  claude mcp list

Answer questions from a separate terminal (same shared DB):

  agent-chat            # auto-refreshing watch console (the default)
  agent-chat web        # browser dashboard at http://127.0.0.1:8765

The shared DB lives at \$ASK_HUMAN_DB (default ~/.claude/ask_human/questions.db).
If 'agent-chat' isn't found, add uv's tool bin to your PATH:  uv tool update-shell
EOF
