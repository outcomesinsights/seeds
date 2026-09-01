---
id: seeds-9
title: "Options modeling: how to handle alternatives and proposals"
status: captured
type: exploration
created_at: 2026-01-28T05:54:10.848060+00:00
updated_at: 2026-01-28T20:53:12.706925+00:00
tags:
  - model
  - architecture
relationships:
  - target_id: seeds-36
    rel_type: relates-to
    created_at: 2026-01-28T05:54:10.848060+00:00
  - target_id: seeds-44
    rel_type: questioned-by
    created_at: 2026-01-28T20:53:13.870179+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

From spec_first_pass.md:

Options appear to be statements with a specific relationship to a topic ('proposed for', 'option for', 'candidate for' - exact relationship TBD).

Example:
Topic: 'what language?'
  - Option: 'use Python' (context: 'AI proposed as fastest for MVP')
  - Option: 'use Go' (context: 'not my strongest language, but Beads uses it')
  - Input: 'whichever is best for AI is fine with me'
  - Resolution: Python ACCEPTED, Go REJECTED

Questions:
1. Are options a distinct seed type, or statements with a relationship?
2. What is the exact relationship between option and topic?
3. What happens to non-selected options when one is accepted?


---
**Partial answers (from conversation):**

Q1: Are options a distinct seed type, or statements with a relationship?
**A: Statements (seeds) with a relationship.** Aligns with 'favor smaller seeds' decision. Each option is its own seed linked to the topic.

Q3: What happens to non-selected options when one is accepted?
**A: Set to rejected status.** The selected option is noted in the parent/topic seed.

Q2 converted to formal question (see attached).
