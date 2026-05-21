#!/bin/bash
set -euo pipefail
MAX_ITERS=${MAX_ITERS:-100}
i=0
while [ "$i" -lt "$MAX_ITERS" ]; do
  if ! grep -q '^- .' .claude/tasks/TODO.md 2>/dev/null; then
    echo "TODO empty, stopping."
    exit 0
  fi
  echo "→ iter $((i+1))"
  claude -p "Take the next task from .claude/tasks/TODO.md per CLAUDE.md"
  i=$((i+1))
done
echo "Reached MAX_ITERS=$MAX_ITERS, stopping."
