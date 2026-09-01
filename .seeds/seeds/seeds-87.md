---
id: seeds-87
title: "Dynamic prime: inject live deliberation state into AI context"
status: captured
type: idea
created_at: 2026-02-24T17:05:47.732381+00:00
updated_at: 2026-05-18T15:58:04.617128+00:00
tags:
  - prime
  - ai-integration
  - beads-inspired
relationships:
  - target_id: seeds-2
    rel_type: relates-to
    created_at: 2026-01-28T05:54:01.142491+00:00
  - target_id: seeds-21
    rel_type: relates-to
    created_at: 2026-01-28T05:56:23.408310+00:00
  - target_id: seeds-130
    rel_type: relates-to
    created_at: 2026-03-12T20:06:54.980356+00:00
  - target_id: seeds-142
    rel_type: relates-to
    created_at: 2026-05-18T15:58:19.686055+00:00
  - target_id: seeds-142.2
    rel_type: relates-to
    created_at: 2026-05-18T15:58:20.305194+00:00
  - target_id: seeds-143
    rel_type: relates-to
    created_at: 2026-05-18T16:44:28.615719+00:00
  - target_id: seeds-169
    rel_type: relates-to
    created_at: 2026-06-15T22:02:27.668195+00:00
  - target_id: seeds-181
    rel_type: relates-to
    created_at: 2026-06-23T20:44:22.761785+00:00
  - target_id: seeds-181.3
    rel_type: relates-to
    created_at: 2026-06-23T20:44:23.754150+00:00
  - target_id: seeds-182
    rel_type: relates-to
    created_at: 2026-06-23T20:44:24.202651+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Seeds' `prime` command outputs static text — a fixed prompt about workflow and capture philosophy. Beads' `bd prime` injects dynamic context: ready work, current state, active items.

Seeds should do the same. A dynamic prime could surface:
- Seeds in `captured` status needing triage (inbox count)
- Seeds in `exploring` status (active deliberation)
- Seeds with unanswered questions (blocking decisions)
- Recently updated seeds (momentum indicators)
- Blocked seeds (resolution bottlenecks)

This makes the AI context injection actionable rather than philosophical. Instead of "here's how to use seeds," it becomes "here's what needs your attention in the deliberation."

The static philosophy text could move to a `--full` flag or only appear on first session, with subsequent primes being purely dynamic state.



---

**Evidence from CSC production usage (2026-04 to 2026-05) — see seeds-142 for the full use-case write-up:**

CSC has 96 seeds. Across 6+ transcript-incorporation sessions, Claude consistently issued 3-6 discovery commands at session start (variants of `seeds list`, `seeds search`, `cat .seeds/seeds.jsonl | grep`, multiple `seeds show <id>`). The static `prime` text provides zero help with this. A digest would replace those commands with zero round trips.

**Concrete digest design proposal:**

`seeds prime` adds a `## Current Seeds` section after the workflow text:
- Counts (total, by status)
- Recently Updated (top N by updated_at — feeds off seeds-recent primitive)
- Active Exploration (status=exploring)
- Open Questions (type=question, status open)
- Tag clusters with counts

Each line: `id status title [tags]` — no body content. Claude can `seeds show <id>` for detail.

Flags: `--no-digest` (opt out), `--digest-limit=N` (default 20 recent + all exploration + all questions).

**Cross-references:** seeds-142 (transcript-incorporation parent), seeds-2 (discoverability question this partially answers).
