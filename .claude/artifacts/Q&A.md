# Q&A

## 2026-05-09 — Hook input parameters

**Q:** what are the params a hook receive in Claude Code?
**A:** Hooks read a JSON payload on stdin with common fields (`session_id`, `transcript_path`, `cwd`, `hook_event_name`) plus event-specific fields (e.g., `tool_name`/`tool_input` for `PreToolUse`, `prompt` for `UserPromptSubmit`, `source` for `SessionStart`). They communicate back via exit code (0 normal, 2 blocking error) or structured JSON on stdout (`decision`, `continue`, `hookSpecificOutput`, etc.), and `$CLAUDE_PROJECT_DIR` is exported for path resolution.

<details><summary>full reply</summary>

## Hook input parameters in Claude Code

Hooks receive a **JSON payload on stdin**. Every event has common fields plus event-specific ones.

### Common fields (all events)
- `session_id` — current session UUID
- `transcript_path` — path to the conversation JSONL
- `cwd` — working directory when the hook fires
- `hook_event_name` — which event triggered the hook

### Event-specific fields

| Event | Extra fields |
|---|---|
| `PreToolUse` | `tool_name`, `tool_input` |
| `PostToolUse` | `tool_name`, `tool_input`, `tool_response` |
| `UserPromptSubmit` | `prompt` |
| `Notification` | `message` |
| `Stop` / `SubagentStop` | `stop_hook_active` (bool — true if hook already fired this stop, used to avoid loops) |
| `PreCompact` | `trigger` (`"manual"` \| `"auto"`), `custom_instructions` |
| `SessionStart` | `source` (`"startup"` \| `"resume"` \| `"clear"` \| `"compact"`) |
| `SessionEnd` | `reason` (`"clear"` \| `"logout"` \| `"prompt_input_exit"` \| `"other"`) |

### Hook output (how it talks back)
- **Exit 0** → stdout shown in transcript mode (or fed back as context for `UserPromptSubmit` / `SessionStart`).
- **Exit 2** → stderr is sent back to Claude as a blocking error (e.g., reject a tool use).
- **Other non-zero** → stderr shown to user, non-blocking.
- **JSON on stdout** for advanced control: `continue`, `stopReason`, `suppressOutput`, `decision` (`"approve"`/`"block"`), `reason`, plus `hookSpecificOutput` (e.g., `additionalContext` for `UserPromptSubmit`/`SessionStart`, `permissionDecision` for `PreToolUse`).

### Environment
- `$CLAUDE_PROJECT_DIR` is set so scripts can resolve project-relative paths regardless of `cwd`.

You can see this live in your own `hooks/shortcuts/actions.py` — it reads stdin via `json.load(sys.stdin)` and inspects `hook_event_name`/`prompt`/`transcript_path`.

</details>
