# artifacts_tree_loop

Hierarchical extension of [`artifacts_loop`](../artifacts_loop/). Replaces the
flat `INDEX.md` + `.claude/artifacts/<SLUG>.md` layout with a **tree of
`INDEX.md` files**: each folder (node) lists its branches, groups, and
leaves, and the agent navigates the tree in progressive-disclosure style
instead of loading the whole index.

Task tracking (`TODO.md` / `DONE.md`) is identical to `artifacts_loop`.

See [`../DESIGN.md`](../DESIGN.md) for the rationale, threshold choices, and
worked examples.

## Files installed

```
.claude/
  tasks/
    TODO.md        ← user appends pending tasks
    DONE.md        ← Claude prepends completed entries
  artifacts/
    INDEX.md       ← root node index (tree starts here)
    MAINTAIN.md    ← write/rebalance protocol; Claude reads this before storing
    L0/            ← root-level leaves
```

Sub-folders (branches), `L1/`, `L2/`, etc. are created on demand as the
tree grows past the fan-out threshold. `CLAUDE.md` itself stays lean and
points at `MAINTAIN.md`, so the bulkier rules only get loaded when the
agent is actually about to write.

## Install

1. Copy `template/.claude/tasks/` and `template/.claude/artifacts/` into your project's `.claude/`.
2. Paste [`template/.claude/CLAUDE.md`](template/.claude/CLAUDE.md) into your project's `.claude/CLAUDE.md`.

## When to use which

- **Flat, small** (<20 artifacts, one topic) → [`artifacts_loop`](../artifacts_loop/).
- **Tree** (this pattern) — >20 artifacts, multiple sub-topics emerging, or context budget pressure from a long flat `INDEX.md`.

Migration from `artifacts_loop` is mechanical: move every existing artifact
into `.claude/artifacts/L0/`, reshape the root `INDEX.md` into the format
in `template/`, then branch/lift on demand.
