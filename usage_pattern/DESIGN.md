# Hierarchical artifacts — design

Extension of [`artifacts_loop`](artifacts_loop/) for projects where the flat
`INDEX.md` + `.claude/artifacts/<SLUG>.md` layout grows beyond what fits
comfortably in an LLM's context. The flat store is replaced by a **tree of
`INDEX.md` files**, navigated in progressive-disclosure style: agents read
the root index, follow the most relevant link, repeat.

Proposed pattern name: **`artifacts_tree_loop/`** (rename freely).

---

## 1. Goals

- **Progressive disclosure.** An agent loads only what its current query
  needs, descending level by level. Never slurps the full corpus.
- **Bounded fan-out.** Each index section lists ~5 entries, not the full
  artifact list. Long flat lists are the failure mode this pattern exists
  to prevent.
- **Symmetric structure.** Every node — root or deep sub-topic — has the
  same shape. No special-case logic per depth.
- **Reorganizable in place.** The tree grows organically; one node can be
  split or lifted without rewriting the rest of the tree.

## 2. Vocabulary

- **Node.** Any folder containing an `INDEX.md`. The root is a node; every
  topic sub-folder is a node.
- **Leaf.** An artifact `.md` file — the actual content. Always stored in
  the node's `L0/` directory.
- **Layer (`L0`, `L1`, `L2`, …).** Aggregation depth *within one node*.
  - `L0/` holds leaves.
  - `L1/` holds **group files** — each summarizes ~5 leaves.
  - `L2/` holds group files that each summarize ~5 `L1` group files. Etc.
- **Branch.** A sub-node (sub-folder) representing a *different topic*.
  Each branch is itself a complete node with its own `L0/`, optional
  `L1/`, optional further branches.
- **Group file.** A markdown file at `L1+` that lists and summarizes its
  children. Used only when there are too many siblings to list in
  `INDEX.md` directly.

## 3. Two organizing forces

A node has two distinct ways to manage growth — and the design pivots on
keeping them separate, because your initial description blended them.

| Force | When to apply | What happens |
|---|---|---|
| **Branch** | Leaves cluster around a *sub-topic distinct from siblings* | New sub-folder (sub-node) is created; matching leaves move into `<sub>/L0/`; the parent's `INDEX.md` replaces N leaf entries with one branch entry. |
| **Lift** | `L0` has many leaves on the *same topic* — splitting further would feel artificial | Cluster leaves into `L1/GROUP_*.md` files (~5 leaves each); the node's `INDEX.md` lists L1 group files instead of L0 leaves; leaves themselves stay put in `L0/`. |

Rule of thumb:
- **Different topics → branch.**
- **Same topic, many items → lift.**

If you can't tell which, don't restructure yet. Leave the leaves in `L0`
and re-evaluate when more arrive.

## 4. Layout

```
.claude/artifacts/
  INDEX.md                       ← root: lists branches + L1 groups + L0 leaves
  L0/                            ← uncategorized / cross-cutting leaves
    QUICK_TAKE_ON_X.md
    ONE_OFF_REPORT.md
  L1/                            ← present only after a lift
    GROUP_MISC_2026_05.md
  coding/                        ← topic branch (a sub-node)
    INDEX.md
    L0/
      REFACTOR_AUTH.md
      ADD_RETRY_LOGIC.md
      ...
    L1/                          ← coding had >threshold leaves → lifted
      AUTH_AND_PERMS.md
      RETRY_AND_BACKOFF.md
    pydantic/                    ← coding branched further
      INDEX.md
      L0/
      L1/
  research/
    INDEX.md
    L0/
```

## 5. File formats

### 5.1 Node `INDEX.md`

```markdown
# <Node title>

<1–2 sentence what-this-node-covers summary.>

Parent: [../INDEX.md](../INDEX.md)        <!-- omit on root -->

## Branches
- [coding/](coding/INDEX.md) — sub-topics for code work
- [research/](research/INDEX.md) — literature & analysis

## L1 groups
- [Auth & perms](L1/AUTH_AND_PERMS.md) — 5 leaves on authn/authz changes
- [Retry & backoff](L1/RETRY_AND_BACKOFF.md) — 3 leaves on resilience

## L0 leaves
- [Quick take on X](L0/QUICK_TAKE_ON_X.md) — one-line description
- [One-off report](L0/ONE_OFF_REPORT.md) — one-line description
```

Skip empty sections. Root has no `Parent:` line.

### 5.2 Group file (`L1/<GROUP>.md`, `L2/<GROUP>.md`, …)

```markdown
# Auth & perms (group)

<2–3 sentence why-these-belong-together summary.>

## Children
- [Refactor auth](../L0/REFACTOR_AUTH.md) — one-line description
- [Add permission checks](../L0/ADD_PERMISSION_CHECKS.md) — one-line description
- ...
```

An `L2` group file has the same shape, but its `Children` point at `L1/*`
group files rather than `L0` leaves.

### 5.3 Leaf (`<SLUG>.md`)

Same as today's `artifacts_loop` leaf, with recommended frontmatter so the
agent can decide similarity programmatically:

```markdown
---
title: Refactor auth flow
tags: [coding, auth]
created: 2026-05-18
---

# Refactor auth flow

… content …
```

## 6. Operating rules

### 6.1 Read protocol

1. Open root `INDEX.md`.
2. Pick the section (Branches → L1 → L0) most relevant to the query.
3. Follow the link. Repeat at the next node / group file.
4. Never load files past where the trail leads.

### 6.2 Write protocol

Two numbers drive the structure:

- **Fan-out target ≈ 5** — aim for ~5 entries per `INDEX.md` section.
- **Restructure threshold = 6** — once a section would list 6 items, take
  the action below.

When producing a new artifact:

1. **Pick a node.** Start at root. Descend into the branch whose topic
   matches. If no branch matches, you land at the current node.
2. **Write the leaf** at `<node>/L0/<SLUG>.md`.
3. **Update `<node>/INDEX.md`** — add a one-line entry under `L0 leaves`
   (or under `L1 groups` if leaves at this node are already lifted; see
   below).
4. **Rebalance if needed**, in this order, at most once per task:
   - **Branch?** If ≥6 leaves in `L0` share a sub-topic distinct from the
     rest, extract them: create `<sub>/`, move leaves to `<sub>/L0/`,
     write `<sub>/INDEX.md`, replace those entries in the parent's
     `INDEX.md` with one Branches entry.
   - **Lift?** Otherwise, if `L0` has ≥6 leaves with no clean sub-topic
     split, cluster them into `L1/GROUP_*.md` files (~5 leaves each).
     Move the listings: parent's `INDEX.md` now shows `L1 groups` instead
     of those `L0 leaves`. Leaves themselves stay in `L0/`.
   - **Cascade.** If `L1` itself reaches 6 files, repeat the lift to
     create `L2`. (Rare; only deep knowledge bases need this.)

Rebalancing is atomic: do it once, at the end of the task, on the node
you just wrote to. Don't preemptively rebalance ancestors or siblings.

### 6.3 Similarity / "same sub-topic"

Two leaves are *similar* if either:
- They share ≥1 tag in their frontmatter, **or**
- Their titles map to the same domain noun (e.g. "auth", "retry",
  "schema migration").

When unsure, **don't branch**. Branching prematurely is harder to undo
than waiting for one more leaf.

### 6.4 Cross-cutting artifacts

An artifact that legitimately belongs to two branches: pick the primary
branch as its home, and add a cross-reference line in the secondary
branch's `INDEX.md` under a `## Cross-refs` section. Never duplicate the
leaf file.

## 7. Diff vs `artifacts_loop`

| Concern | `artifacts_loop` | `artifacts_tree_loop` |
|---|---|---|
| Leaf location | `.claude/artifacts/<SLUG>.md` (flat) | `<node>/L0/<SLUG>.md` |
| Index | one `INDEX.md` | tree of `INDEX.md` files |
| Write step | append to `INDEX.md` | append to nearest node's `INDEX.md`, then rebalance once if a threshold tripped |
| Rebalance | n/a | branch or lift at ≥6 items |
| Task tracking | `TODO.md` / `DONE.md` | unchanged |

`DONE.md` entries should link to the leaf's *full path* (e.g.
`artifacts/coding/L0/REFACTOR_AUTH.md`) rather than the slug.

## 8. When to use this pattern

Use `artifacts_tree_loop` when:
- Artifact count is or will become **>20**.
- Multiple distinct sub-topics are emerging.
- Agents waste context loading the full `INDEX.md`.

Stick with flat `artifacts_loop` when:
- Artifact count <20.
- Single coherent topic.
- Restructure overhead would dwarf the benefit.

Migration from flat → hierarchical is mechanical: move every existing
artifact into `.claude/artifacts/L0/`, rename `INDEX.md` to the root
`INDEX.md` in the new format, then branch/lift on demand.

## 9. Things deliberately left open

- **Auto-rebalance vs ask-first.** First cut: agent rebalances autonomously
  whenever a threshold trips. Could later require user OK for branch
  creation only (lift is safer / more reversible).
- **Search.** This tree is for *navigation*. Full-text search is `git grep`
  over `L0/`, or a separately maintained flat `INDEX_FLAT.md` regenerated
  on demand.
- **Naming of group files at L1+.** No strict convention yet; suggest
  `UPPER_SNAKE_CASE` matching the dominant tag or theme of its children.
- **Reverse moves.** "De-branching" (merging a sparse sub-node back into
  parent) isn't specified. Likely rare; cross that bridge when it appears.

## 10. Why this beats the original sketch

Your original phrasing had one mechanism — "if similar, create a block;
if >5 files, create L1" — doing two different jobs. Separating **branch**
(topic split, new folder) from **lift** (vertical aggregation, same
folder) gives the agent a clear decision tree instead of a single
overloaded "what do I do when things grow" rule, and lets the same
structure serve both broad knowledge bases (lots of branching) and deep
ones (lots of lifting within a branch).

The rest — symmetric nodes, parent links, fan-out of 5, atomic
rebalance — is just discipline that keeps the tree LLM-legible.
