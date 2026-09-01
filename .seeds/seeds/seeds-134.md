---
id: seeds-134
title: "Resolution capture: resolved seeds need a discrete 'resolution' field"
status: resolved
type: decision
created_at: 2026-03-20T20:12:59.834022+00:00
updated_at: 2026-03-20T20:30:02.592090+00:00
resolved_at: 2026-03-20T20:30:02.592082+00:00
resolution: "Implemented: added 'resolution' field to Seed model, DB schema, CLI (resolve --resolution, abandon --reason), show output, JSONL export/import, FTS search, and web UI. Migration auto-adds column to existing DBs."
tags:
  - model
  - lifecycle
  - resolution
  - architecture
converted_at: 2026-09-01T05:20:22.746832+00:00
---

When a seed is marked resolved, the most valuable piece of the deliberation — what was actually decided or what happened — has nowhere to go. Currently resolve just flips the status with no record of the outcome.

Proposal: add a first-class 'resolution' text field, distinct from notes or content. This field only applies when a seed reaches a terminal state (resolved, abandoned). It should be easily accessible — when you look back at a resolved seed, the resolution is the thing you most want to see.

Design considerations:
- Discrete field, not appended to notes (too generic, gets buried)
- Should 'seeds resolve' require a resolution, or allow optional with encouragement?
- Abandoned seeds likely benefit from a similar 'reason' field (or share the same field)
- The resolve CLI command needs a --resolution flag (e.g., seeds resolve seed-1234 --resolution "Shipped in PR #42")
- Display: resolution should be prominently shown in 'seeds show' output for resolved seeds
- Export: resolution field should appear in JSONL export

A seed can stay open forever — that's fine. But if someone takes the time to mark it resolved, capturing the outcome is the whole point of a deliberation tool.
