---
id: seeds-lcfa.6.1
title: Full-text search is the ONE real casualty of dropping SQLite — it needs an answer before anything is deleted
status: resolved
type: concern
parent: seeds-lcfa.6
created_at: 2026-08-26T04:02:37.005874+00:00
updated_at: 2026-08-31T21:41:45.880104+00:00
resolved_at: 2026-08-31T21:41:45.880094+00:00
resolution: "Answered (@aguynamedryan, 2026-08-31): ranked full-text search does not survive, and that is accepted rather than mitigated. This seed asked for an answer before anything was deleted, and it got one on the evidence it asked for — usage, not capability: roughly 15 genuine 'seeds suggest' invocations across 5 sessions in the whole project transcript history, mostly agent-initiated during dedup passes. Porter stemming is a real casualty ('merging' stops finding 'merge'); the offsetting measurement is that grep tested broader than FTS on a real query, 72 hits vs 77, including one FTS missed. seeds search becomes ripgrep; suggest, sanitize_fts_query and the seeds_fts* tables are removed in phase 5 of plans/storage-overhaul.md. Efficacy: the seed did its job exactly as filed — it named the one thing that could not be waved through, and it blocked seeds-lcfa.6 until it was settled."
tags:
  - fts
  - search
  - sqlite
  - per-seed-files
  - blocker
  - 2026-08-25
relationships:
  - target_id: seeds-fkb8
    rel_type: relates-to
    created_at: 2026-08-28T16:33:00.336067+00:00
  - target_id: seeds-ebg1
    rel_type: relates-to
    created_at: 2026-08-28T17:09:42.933080+00:00
  - target_id: seeds-sdhc
    rel_type: relates-to
    created_at: 2026-08-28T17:36:41.767861+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Pulled out of the per-seed-files prototype (seeds-lcfa.6) because it is the single thing that genuinely breaks, and burying it in a longer seed is how it gets discovered halfway through an implementation instead of before one.

WHAT EXISTS TODAY. src/seeds/db.py:159-190 defines `seeds_fts`, an FTS5 virtual table over title, content, tags and resolution, kept current by AFTER INSERT / AFTER UPDATE triggers on the seeds table. The `.seeds/seeds.db` schema confirms the full FTS5 family: seeds_fts, seeds_fts_config, seeds_fts_content, seeds_fts_data, seeds_fts_docsize, seeds_fts_idx. This is real, working functionality that nothing else in the proposed architecture replaces.

WHY IT IS THE ONLY CASUALTY. Everything else SQLite does for seeds is comfortably within reach of plain Python at this scale — measured 2026-08-25, reading and filtering all 280 seed records takes 47 ms, and 5,040 takes 297 ms. Ranked full-text search is the exception: there is no stdlib equivalent, and ranking is the part that matters, not just matching.

THE OPTIONS, roughly in order of weight:
1. Brute-force scan on every search. At 280 seeds this is instant and honestly fine; at 5,000 it is a few hundred ms. No dependency, no index to keep current, no staleness bug possible. The catch is ranking — substring matching gives hits, not relevance, and today FTS5 gives bm25 ordering for free.
2. A small inverted index rebuilt from the files, cached in a gitignored derived file. Keeps ranking, keeps zero runtime dependencies, but reintroduces exactly the thing per-seed files were meant to eliminate: a derived artifact that can be stale. It is far less dangerous than today's situation because it is rebuildable from the files in milliseconds and never holds unique data — but it must be treated as a cache, with a cheap staleness check, not as a store.
3. DuckDB's fts extension. Real ranking, but it drags in a 21 MB wheel to serve one command, against a runtime dependency list that is about to be just `click`.
4. Keep a SQLite file purely as a derived FTS index. Ironic but coherent: files stay the source of truth, SQLite becomes a disposable search cache, and FTS5 keeps working unchanged. Probably the least-code path if ranking must be preserved.

WHAT TO DECIDE FIRST, and it is a usage question rather than a technical one: does anyone actually use ranked search over these seeds, or is search in practice "find the seed about X" over a few hundred records where any match order is acceptable? If the latter, option 1 wins outright and this stops being a blocker. That should be checked before any of the heavier options gets designed.
