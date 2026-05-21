#!/bin/bash
set -euo pipefail

export BEADS_ACTOR="${BEADS_ACTOR:-${USER}-loop-$$}"
echo "Loop actor: ${BEADS_ACTOR}"

MAX_ITERS=${MAX_ITERS:-100}
mkdir -p logs
i=0

while [ "$i" -lt "$MAX_ITERS" ]; do
  next=$(bd ready --json --limit 1 2>/dev/null | jq -r '(.data // .)[0].id // ""')
  if [ -z "$next" ]; then
    echo "no ready tasks, sleeping 10s"
    sleep 10
    continue
  fi

  if ! bd update "$next" --claim >/dev/null 2>&1; then
    echo "  claim failed for $next, sleeping 5s"
    sleep 5
    continue
  fi

  mkdir -p ".claude/tasks/$next"
  ts=$(date +%Y%m%d-%H%M%S)
  log="logs/iter-$ts.log"
  echo "→ iter $((i+1)): claimed $next"

  if ! claude -p "You are assigned task $next. Artifact dir: .claude/tasks/$next/. Follow CLAUDE.md." >"$log" 2>&1; then
    echo "  claude exited non-zero, releasing $next"
    bd update "$next" --status ready --assignee "" --notes "loop.sh: released after non-zero exit" >/dev/null 2>&1 || true
  fi

  i=$((i+1))
done
echo "Reached MAX_ITERS=$MAX_ITERS, stopping."
