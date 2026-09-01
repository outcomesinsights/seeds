---
id: seeds-42
title: Would a graph database be better than SQLite if relationships become central?
status: deferred
type: question
created_at: 2026-01-28T20:52:40.394081+00:00
updated_at: 2026-08-26T04:01:42.432189+00:00
tags:
  - architecture
  - storage
relationships:
  - target_id: seeds-170
    rel_type: relates-to
    created_at: 2026-06-15T22:02:27.902972+00:00
  - target_id: seeds-lcfa
    rel_type: relates-to
    created_at: 2026-08-26T03:35:17.931292+00:00
  - target_id: seeds-lcfa.6
    rel_type: relates-to
    created_at: 2026-08-26T04:01:42.547832+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

If relationships become central to how seeds work (options, answers, parents, related-to, etc.), a graph database might be more natural than SQLite with JSON columns.

Defer until we understand relationship patterns better. SQLite is fine for MVP.


--- SURVEYED AND EFFECTIVELY ANSWERED (2026-08-25) ---

This seed deferred the storage-engine question until relationship patterns were understood. A full engine survey ran in the Dolt deliberation (seeds-lcfa and its children) and the answer it produced is: no engine change. Not a graph database, not Dolt, not DuckDB.

The two findings that settle it:

1. RELATIONSHIPS NEVER BECAME CENTRAL ENOUGH TO NEED AN ENGINE. The whole graph today is one `relationships` table with a target id and a rel_type, plus hierarchical ids that encode parentage in the id itself. Measured 2026-08-25: 280 seeds, and the entire database is read and filtered in pure Python in 47 ms — most of that interpreter startup. At 18x scale (5,040 seeds) it is 297 ms. Graph traversal at this size is not a query-planning problem.

2. THE ENGINE WAS NEVER THE PROBLEM. The pain that reopened this whole area was cross-host sync, not query power (seeds-lcfa.1). The candidate answer that came out of it moves in the opposite direction from a bigger engine: store each seed as its own file, let git merge them, and let the database become a derived index — or disappear entirely (seeds-lcfa.6). DuckDB, tested for exactly this, was SLOWER than plain Python at both 280 and 5,040 seeds, and earns its place only as a cross-repo reader (see seeds-183), never as the store.

WHAT WOULD REOPEN IT: relationship queries that are genuinely recursive and unbounded — "show me every seed reachable from this one, at any depth, with path" across tens of thousands of seeds. Nothing in the current usage comes close.

Recommend resolving this rather than leaving it deferred, with the resolution being "no — the survey went the other way," and pointing at seeds-lcfa.3 for the measured reasoning.
