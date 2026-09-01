---
id: seeds-86
title: "Ephemeral vs persistent: beads wisps applied to seeds"
status: captured
type: idea
created_at: 2026-02-24T17:05:47.446866+00:00
updated_at: 2026-02-24T17:05:56.745179+00:00
tags:
  - ephemeral
  - lifecycle
  - beads-inspired
relationships:
  - target_id: seeds-45
    rel_type: relates-to
    created_at: 2026-01-28T20:59:43.550599+00:00
  - target_id: seeds-12.1
    rel_type: relates-to
    created_at: 2026-02-24T17:05:11.482022+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Beads v0.50+ introduced a phase system for issue lifecycle:

| Phase | Name | Synced | Purpose |
|-------|------|--------|---------|
| Solid | Proto | Yes | Frozen template |
| Liquid | Mol | Yes | Active persistent work |
| Vapor | Wisp | No | Ephemeral, garbage-collectible |

Seeds has an analogous tension: a quick `seeds jot "hmm maybe X"` has the same weight as a carefully explored decision with attached questions and resolved children. Everything is persistent, everything goes in the JSONL, everything shows in `seeds list`.

**What seeds could adopt:**
- Jots start as ephemeral (wisp-like) — not exported to JSONL, not shown by default in list
- `seeds promote <id>` graduates a jot to a persistent seed when it proves worthwhile
- `seeds gc` cleans up old ephemeral jots that never went anywhere
- This reduces noise in the deliberation record and makes the JSONL export more meaningful

**Key difference from beads:**
In beads, wisps are about operational overhead (routine patrol, scaffolding). In seeds, ephemeral capture is about *cognitive overhead* — lowering the barrier to capturing half-formed thoughts without polluting the deliberation record. The metaphor shifts from "operational lifecycle" to "thought maturity."
