---
id: seeds-16
title: "Everything is a seed: polymorphic model (statement, topic, question)"
status: captured
type: decision
created_at: 2026-01-28T05:55:39.401266+00:00
updated_at: 2026-02-24T17:04:37.698223+00:00
tags:
  - model
  - architecture
relationships:
  - target_id: seeds-32
    rel_type: relates-to
    created_at: 2026-01-28T05:55:39.401266+00:00
  - target_id: seeds-34
    rel_type: relates-to
    created_at: 2026-01-28T05:55:39.401266+00:00
  - target_id: seeds-35
    rel_type: relates-to
    created_at: 2026-01-28T05:55:39.401266+00:00
  - target_id: seeds-41
    rel_type: relates-to
    created_at: 2026-01-28T05:55:39.401266+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

From spec_first_pass.md: 'Seeds are the fundamental unit. Deliberation is the activity of working through seeds, not a separate entity or container.'

A seed can be:
- Statement: An assertion, proposal, or decision (e.g., 'use SQLite')
- Topic: A subject requiring deliberation (e.g., 'storage approach', 'what language?')
- Question: Something needing an answer (e.g., 'how do we handle concurrent writes?')

The type affects how resolution works, but the underlying entity is always a seed.

This is a design decision that was made for MVP (see SeedType enum in mvp.md).



---
**Tensions and open questions (consolidated from seed-55de, seed-c432):**

**Type mismatch (from seed-55de):**
MVP implemented types: idea, question, decision, exploration, concern
Spec described types: statement, topic, question
These don't align - need to reconcile or document why they diverged.

**Topic/question overlap (from seed-c432):**
'storage approach' (topic) vs 'how do we store data?' (question) express the same thing.
Suggests topic and question may be the same concept phrased differently.
If so, do we need both? Or is the distinction meaningful (declarative vs interrogative framing)?


---
**Beads v0.50-v0.56 simplification precedent (Feb 2026):**

Beads removed ~27,000 lines of code in this release cycle: daemon/RPC subsystem, JSONL sync layer, SQLite backend, 3-way merge engine, storage factory/provider abstraction, tombstone/soft-delete system. The dominant philosophy was: if you can remove a classification axis or abstraction layer without losing information, do it.

This validates the "types could be inferred from relationships" direction. If a seed has children that are alternatives → it's a decision. If it has unanswered questions → it's an exploration. The type enum may be unnecessary weight. Beads' experience says radical simplification pays off.
