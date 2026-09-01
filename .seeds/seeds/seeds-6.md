---
id: seeds-6
title: "Relationship types: what relationships do we need?"
status: exploring
type: exploration
created_at: 2026-01-28T05:54:02.752699+00:00
updated_at: 2026-03-12T15:19:27.671872+00:00
tags:
  - model
  - architecture
relationships:
  - target_id: seeds-123
    rel_type: relates-to
    created_at: 2026-01-28T05:54:02.752699+00:00
  - target_id: seeds-124
    rel_type: relates-to
    created_at: 2026-01-28T05:54:02.752699+00:00
  - target_id: seeds-20
    rel_type: relates-to
    created_at: 2026-01-28T05:54:02.752699+00:00
  - target_id: seeds-88
    rel_type: relates-to
    created_at: 2026-01-28T05:54:02.752699+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

From spec_first_pass.md, relationship types identified:

- Parent/child: Seeds can be nested; parent cannot resolve until children resolve
- Option-for/proposed-for: Alternatives for a topic/decision
- Constraint-on: Limitations that affect a seed
- Related-to: Loose coupling
- Answers: Question-answer relationship
- Supersedes: One seed replaces another

Additional concepts:
- Explicit vs Possible relationships: Confirmed vs AI-suggested connections
- Relationship discovery can happen at creation, during review, or on demand
- No seed is ever truly 'permanently standalone' - new seeds might create relationships later


---
**Beads v0.50-v0.56 validation (Feb 2026):**

Beads now implements typed relationships in production. Four relationship types beyond blocking:
- `relates_to` — bidirectional "see also" (what seeds has today)
- `replies_to` — message/reasoning threading
- `duplicates` — deduplication with auto-close of the duplicate
- `supersedes` — version chains with auto-close of the superseded item

Plus existing blocking types: `blocks`, `parent-child`, `conditional-blocks`, `waits-for`, `discovered-from`.

For seeds, `supersedes` is the highest-value addition — decisions evolve and tracking which decision replaced which is core to deliberation. `duplicates` is also valuable as the seed database grows. `replies_to` could enable reasoning chains.

## Design Decisions (2026-03-12)

Analysis of production data (114 seeds, 36 questions, 65 related_to links) identified these patterns:

**Initial relationship types (v1):**
- `questions` — directed: question-seed → seed it asks about (36 instances)
- `answers` — directed: for when a separate seed answers a question (25 answered questions)
- `relates-to` — bidirectional placeholder for 'not yet specifically typed' (65 links)

**Observed but deferred patterns (still as relates-to):**
- Decision → Idea (~15 links, e.g. 5 web UI decisions all pointing at seed-5f7b)
- Concern → Topic (~12 links, clustering around umbrella concerns)
- Exploration → Topic (~8 links)

**Discovery process:** New types added to enum as patterns emerge from reviewing relates-to edges. Periodic triage of relates-to links extracts specific types. Evolutionary, not speculative.

**Blocking:** Unresolved question-seeds block parent seed resolution, same as unresolved children. Mirrors beads' blocking concept.
