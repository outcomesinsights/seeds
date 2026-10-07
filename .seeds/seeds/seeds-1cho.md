---
id: seeds-1cho
title: 'list --sort status: order a tag-filtered list by column so a focus set reads as a board'
status: deferred
type: idea
created_at: 2026-10-07T18:50:12.075908+00:00
updated_at: 2026-10-07T18:50:21.398783+00:00
tags:
  - focus-set
  - board
  - list
  - deferred
relationships:
  - target_id: seeds-c5wy
    rel_type: relates-to
    created_at: 2026-10-07T18:50:21.398174+00:00
---

Split out of seeds-c5wy when Ryan ruled tags-only on 2026-10-07: "let's not worry about sort right now and just use tags." DEFERRED, not rejected.

The proposal: `seeds list --sort status` orders lines by the `SeedStatus` enum, so `seeds list --tag focus --sort status` reads as a board, one block per column. It is about 3 lines in `store.list_seeds` plus the Click choice, and it works for every filter, not just focus sets. The alternative is `--group-by status`, which prints a `## exploring (n)` header per column, about 10 lines. Pick one, not both.

Revisit if reading `seeds list --tag focus` with interleaved statuses turns out to be a real annoyance in practice.
