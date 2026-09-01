---
id: seeds-h5rq
title: "seeds cutting: context-carrying capture, the vegetative sibling of jot"
status: captured
type: decision
created_at: 2026-09-01T16:29:11.606858+00:00
updated_at: 2026-09-01T16:29:53.019105+00:00
tags:
  - cutting
  - capture
  - workflow
  - ai-ux
  - naming
  - command
  - 2026-09-01
relationships:
  - target_id: seeds-14
    rel_type: relates-to
    created_at: 2026-09-01T16:29:52.726491+00:00
  - target_id: seeds-112.2
    rel_type: relates-to
    created_at: 2026-09-01T16:29:52.871912+00:00
  - target_id: seeds-74.2.2
    rel_type: relates-to
    created_at: 2026-09-01T16:29:53.018536+00:00
---

**Ruled 2026-09-01 (Ryan): the command is named `cutting`.**

## Problem

In a long-running session, several distinct topics surface, each warranting its own
thread. Working one topic means the others fall by the wayside — not because they were
rejected, but because nothing durable holds them. This is seeds-14 ("mind racing")
observed from the agent side rather than the human side.

`jot` is the existing answer and it is not sufficient here. A jot captures the
*statement* of a topic. What gets lost is the *context* — the surrounding argument that
made the topic worth raising. Restarting from a one-line jot means restarting cold, and
the cost of that restart is why parked topics stay parked.

## The command

`seeds cutting` — capture a live mid-conversation topic together with enough of the
surrounding deliberation to resume it cold.

## Why the name (this is the load-bearing part)

Seeds already contains two propagation modes; horticulture already names them, and the
names carry the exact distinction we need:

- **`jot`** = *seed propagation*. Sown from nothing. The new plant carries no parent
  tissue. A statement-only capture.
- **`cutting`** = *vegetative propagation*. Living tissue snipped from the parent, which
  roots on its own and carries the parent's material with it. A context-carrying capture.

The statement-vs-context fork IS the seed-vs-vegetative distinction. Naming it `cutting`
makes the command pair teach the difference instead of documenting it.

Grammatically consistent with `seeds trellis <id>` — noun-as-verb is established style in
this CLI.

## Alternatives considered and rejected

- **`park`** — the original working name. Not horticultural, and it describes storage
  rather than propagation.
- **`transplant`** — legible to non-gardeners, root ball = context. Rejected: implies a
  destination already exists, and it does not.
- **`pot` / `pot up`** — real term for moving a seedling to its own container, matches
  "own thread" well. Rejected: reads as storage and drifts toward `defer`.
- **`heel in`** — horticulturally the most precise (temporarily trench bare-root stock to
  keep it alive until you can plant it properly; explicitly not-its-final-home).
  Rejected: obscure, and two words.

## Constraint on any implementation

`defer` already occupies "set aside for later." `cutting` must earn its place on
**context capture**, not on deferral — otherwise it is a synonym and users will conflate
the two. This is the bar the name had to clear, and the reason `pot` did not.

## Status

Deliberation only. NOT authorized for implementation — promote to beads first.
