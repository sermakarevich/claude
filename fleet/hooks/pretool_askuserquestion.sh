#!/bin/sh
# Fleet PreToolUse hook — denies AskUserQuestion in headless fleet mode.
# Invoked by Claude Code's PreToolUse hook when the agent attempts AskUserQuestion.
# Emits a corrective message and exits 2 to deny the tool call.

cat >&2 <<'EOF'
AskUserQuestion is not available in headless fleet mode.
To ask the human a question:
  1. Append a "## Q: <your question>" block to Q&A.md.
  2. Run: bd update <task_id> --status blocked --notes "QUESTION: <one-line>"
  3. Optionally: bd comment <task_id> "<longer context>"
  4. Exit cleanly.
See CLAUDE.md (Q&A protocol section) for full details.
EOF

exit 2
