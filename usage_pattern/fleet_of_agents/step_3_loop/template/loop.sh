#!/bin/bash
set -euo pipefail
i=0
while :; do
  if ! grep -q '^- .' .claude/tasks/TODO.md 2>/dev/null; then
    echo "TODO empty, sleeping 10s"
    sleep 10
    continue
  fi
  echo "→ iter $((i+1))"
  claude -p "Take the next task from .claude/tasks/TODO.md per CLAUDE.md"
  i=$((i+1))
done
