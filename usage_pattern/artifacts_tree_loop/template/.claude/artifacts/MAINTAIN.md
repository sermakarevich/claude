# Artifact store maintenance

How to store, navigate, and restructure the artifact tree under `.claude/artifacts/`. 

## Layout

```
.claude/artifacts/
  INDEX.md                ← root node
  MAINTAIN.md             ← this file
  L0/<SLUG>.md            ← leaves (actual artifacts)
  L1/<GROUP>.md           ← group files, ~5 leaves each (created by Lift)
  L2/<GROUP>.md           ← summarize ~5 L1 groups (rare)
  <branch>/               ← sub-node for a different topic; same shape recursively
```

A **node** is any folder with `INDEX.md`. A **leaf** is an `.md` artifact in some node's `L0/`. `L0/L1/L2...` are aggregation layers *within one node*; sub-folders are **branches** for *different topics*.

## Storing a new artifact

1. **Pick a node**: start at root, descend into the branch whose topic matches; no match → land here.
2. Write the leaf at `<node>/L0/<SLUG>.md` (UPPER_SNAKE_CASE; frontmatter `tags` recommended).
3. Add a one-line entry to `<node>/INDEX.md` under `## L0 leaves` (or `## L1 groups` if already lifted).
4. **Rebalance** if that section now has ≥6 items — at most one rebalance per task, on the node you wrote to:
   - **Branch** — if ≥6 leaves share a sub-topic distinct from the rest: create `<sub>/`, move those leaves to `<sub>/L0/`, write `<sub>/INDEX.md`, replace those entries in the parent's `INDEX.md` with one Branches entry.
   - **Lift** — otherwise: cluster L0 into `L1/GROUP_*.md` files (~5 leaves each), move listings from `## L0 leaves` to `## L1 groups`. Leaves stay in `L0/`.
   - **Cascade** — if `L1` itself hits 6, lift again to `L2`.

**Different topics → branch; same topic, many items → lift.** When unsure, don't restructure. Two leaves are similar if they share ≥1 `tags` entry or their titles map to the same domain noun.

Cross-cutting leaf: pick one branch as home, add a `## Cross-refs` line in the other. Never duplicate the file.

## Reading the tree

Open root `INDEX.md`, follow the most relevant link, repeat. Each step gives summaries; don't load files past where the trail leads.

## File formats

**Node `INDEX.md`** — skip empty sections; root omits `Parent`:

```
# <Title>
<1–2 sentence summary.>
Parent: [../INDEX.md](../INDEX.md)

## Branches
- [coding/](coding/INDEX.md) — sub-topics for code work
## L1 groups
- [Auth & perms](L1/AUTH_AND_PERMS.md) — 5 leaves on authn/authz
## L0 leaves
- [Quick take on X](L0/QUICK_TAKE_ON_X.md) — one-line description
## Cross-refs
- [Refactor auth](../coding/L0/REFACTOR_AUTH.md) — primary in coding/
```

**Group file** (`L1/<GROUP>.md`; `L2/<GROUP>.md` links `../L1/*` instead):

```
# <Title> (group)
<2–3 sentence why-together summary.>

## Children
- [Leaf title](../L0/LEAF_SLUG.md) — one-line description
```

**Leaf** (`<node>/L0/<SLUG>.md`):

```
---
title: <Human title>
tags: [topic1, topic2]
created: YYYY-MM-DD
---
# <Title>
… content …
```
