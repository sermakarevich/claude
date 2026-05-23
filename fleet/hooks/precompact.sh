#!/bin/sh
# Fleet PreCompact hook — signals context pressure to the supervisor.
# Invoked by Claude Code's PreCompact hook event before auto-compaction.
# Exits 2 to halt the agent; the TaskRunner detects the flag file after exit.

if [ -z "${FLEET_ARTIFACT_DIR:-}" ]; then
    echo "fleet precompact hook: FLEET_ARTIFACT_DIR not set; skipping context-pressure signal" >&2
    exit 0
fi

touch "${FLEET_ARTIFACT_DIR}/.context_pressure"
exit 2
