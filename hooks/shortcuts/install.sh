#!/usr/bin/env bash
# install.sh — register shortcuts in ~/.claude/settings.json for both
# UserPromptSubmit and Stop events.
#
# Idempotent and migration-aware: any existing entry referencing this hook.py
# under either event is dropped before reinstalling. Other unrelated hooks are
# preserved untouched.
#
# Requires: jq, claude CLI. No ANTHROPIC_API_KEY needed — the hook shells out
# to `claude -p` which reuses your existing Claude Code auth.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK_PATH="$SCRIPT_DIR/hook.py"
SETTINGS="$HOME/.claude/settings.json"
CMD="python3 \"$HOOK_PATH\""
EVENTS=(UserPromptSubmit Stop)

for dep in jq claude; do
  if ! command -v "$dep" >/dev/null 2>&1; then
    echo "error: '$dep' is required but not found in PATH" >&2
    exit 1
  fi
done

if [[ ! -f "$HOOK_PATH" ]]; then
  echo "error: hook.py not found at $HOOK_PATH" >&2
  exit 1
fi
chmod +x "$HOOK_PATH"

mkdir -p "$(dirname "$SETTINGS")"
[[ -f "$SETTINGS" ]] || echo '{}' > "$SETTINGS"

for event in "${EVENTS[@]}"; do
  # Drop any existing $event entry referencing this hook.py; preserve siblings.
  tmp=$(mktemp)
  jq --arg p "$HOOK_PATH" --arg ev "$event" '
    .hooks //= {} |
    .hooks[$ev] //= [] |
    .hooks[$ev] |= map(
      .hooks //= [] |
      .hooks |= map(select((.command // "") | contains($p) | not)) |
      select((.hooks | length) > 0)
    )
  ' "$SETTINGS" > "$tmp"
  mv "$tmp" "$SETTINGS"

  # Append the current command under $event.
  tmp=$(mktemp)
  jq --arg cmd "$CMD" --arg ev "$event" '
    .hooks //= {} |
    .hooks[$ev] //= [] |
    .hooks[$ev] += [{"hooks": [{"type": "command", "command": $cmd}]}]
  ' "$SETTINGS" > "$tmp"
  mv "$tmp" "$SETTINGS"

  echo "registered $event hook in $SETTINGS"
done

echo
echo "command: $CMD"
echo
echo "Uses 'claude -p' and reuses your existing Claude Code auth — no ANTHROPIC_API_KEY needed."
echo
echo "Next steps:"
echo "  Start a prompt with 'fix:' to capture instructions, or 'q:' to log a Q&A."
echo "  Artifacts land at <cwd>/.claude/artifacts/{INSTRUCTIONS,Q&A}.md (auto-created)."
echo
echo "Logs: $SCRIPT_DIR/logs/hook.log"
