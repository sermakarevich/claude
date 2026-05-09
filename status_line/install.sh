#!/usr/bin/env bash
# Install the status line script and wire it into ~/.claude/settings.json.
#
# Copies status_line.sh to ~/.claude/status_line/status_line.sh, updates
# settings.json's `statusLine.command` to the new path, and removes any
# legacy ~/.claude/status_line.sh file. Backs up settings.json first.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$HOME/.claude/status_line"
TARGET_SH="$TARGET_DIR/status_line.sh"
SETTINGS="$HOME/.claude/settings.json"

echo "Installing status line"
echo "  source : $SCRIPT_DIR/status_line.sh"
echo "  target : $TARGET_SH"

mkdir -p "$TARGET_DIR"
cp "$SCRIPT_DIR/status_line.sh" "$TARGET_SH"
chmod +x "$TARGET_SH"

if [ ! -f "$SETTINGS" ]; then
    echo "Error: $SETTINGS not found." >&2
    exit 1
fi

backup="$SETTINGS.bak.$(date +%Y%m%d_%H%M%S)"
cp "$SETTINGS" "$backup"
echo "  backup : $backup"

# Update statusLine.command, preserving any other fields it had.
python3 - "$SETTINGS" <<'EOF'
import json, sys
path = sys.argv[1]
with open(path) as f:
    s = json.load(f)
sl = s.setdefault("statusLine", {})
sl["type"] = "command"
sl["command"] = "bash ~/.claude/status_line/status_line.sh"
with open(path, "w") as f:
    json.dump(s, f, indent=2)
    f.write("\n")
EOF

# Remove legacy script (no longer referenced).
rm -f "$HOME/.claude/status_line.sh"

echo
echo "Done. Restart Claude Code to pick up the new status line."
