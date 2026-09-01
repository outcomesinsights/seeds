---
id: seeds-49
title: "Confusion: 'question' exists as both seed type AND separate attached object"
status: exploring
type: concern
created_at: 2026-01-28T21:00:22.070848+00:00
updated_at: 2026-03-12T15:19:26.921760+00:00
tags:
  - model
  - architecture
relationships:
  - target_id: seeds-32
    rel_type: relates-to
    created_at: 2026-01-28T17:30:18.827899+00:00
  - target_id: seeds-123
    rel_type: relates-to
    created_at: 2026-01-28T21:00:22.070848+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Current model has:
1. SeedType.QUESTION - a seed whose type is 'question'
2. Question object - attached to seeds via 'seeds ask', has its own id and status

This is confusing. Are they the same concept? Different? When use which?

May relate to seed-29c0 (question vs exploration difference).



---
**Consolidated from seed-d6e2, seed-8920, seed-29c0:**

**Why this matters (from seed-d6e2):**
Questions embedded as prose in seed content lose lifecycle tracking. We can't mark Q1 answered and Q2 deferred. They need formal status tracking.

**Possible resolutions:**
1. Question objects attached via 'seeds ask' (have their own id/status) - current MVP approach
2. Seeds of type=question, linked to parent topic
3. Hybrid: only use Question objects, deprecate question as seed type

**Open sub-questions:**
- How are answers recorded? (In Question.answer field? Separate seed?)
- What's the difference between question and exploration seed types?
- When should user create seed type=question vs use 'seeds ask'?

## Resolution Direction (2026-03-12)

Decision made: questions become seeds. The Question dataclass and questions table are being removed. Questions will be seeds of type=question, linked to their parent seed via a `questions` relationship edge in the new relationships table.

Answer recording: the question-seed's content field holds the answer text, and its status moves to RESOLVED when answered. The `answers` relationship type exists for cases where a separate seed provides the answer.

This also resolves the 'when to use seed type=question vs seeds ask' confusion — there's only one path now: `seeds ask` creates a question-type seed with a relationship.
