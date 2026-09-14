---
id: seeds-taff
title: How should sweep mode pick its window — ask the user, default to ~30 days, infer from the most recent resolved timestamp in the store, or write a marker at the end of each run?
status: resolved
type: question
created_at: 2026-09-14T03:43:38.953333+00:00
updated_at: 2026-09-14T03:51:58.321529+00:00
resolved_at: 2026-09-14T03:51:58.321520+00:00
relationships:
  - target_id: seeds-152.6
    rel_type: questions
    created_at: 2026-09-14T03:43:38.955024+00:00
---

Ruled (Ryan, 2026-09-13): default ~30 days, with --since to override. Stateless and predictable; no marker state to track or merge across hosts. Accepted cost: a gap longer than the window silently misses its early span, and nothing flags it. Mitigated by the verb printing the window it used.
