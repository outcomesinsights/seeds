---
id: seeds-8
title: "Resolution mechanics: how does resolving work for different seed types?"
status: captured
type: question
created_at: 2026-01-28T05:54:10.461591+00:00
updated_at: 2026-03-11T20:50:18.651947+00:00
tags:
  - model
  - architecture
relationships:
  - target_id: seeds-118
    rel_type: relates-to
    created_at: 2026-01-28T05:54:10.461591+00:00
  - target_id: seeds-19
    rel_type: relates-to
    created_at: 2026-01-28T05:54:10.461591+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

From spec_first_pass.md:

Questions:
- Does accepting an option automatically reject alternatives?
- What does resolution look like for different seed types (topic vs question vs statement)?

For topics with options:
- When a topic resolves by accepting one option, what happens to other options?
- Are they automatically rejected? Or need explicit rejection?
- Or are they 'superseded' by the accepted option?

Terminal states: accepted, rejected, abandoned, superseded
All seeds ultimately reach a terminal state.



---
**Question closure specifics (consolidated from seed-fcd3):**

Multiple answerers possible:
- AI can research and provide an answer
- Human can provide an answer
- Multiple answers might exist

Closure requirements:
- Questions need explicit 'answered' state
- Closure includes attribution (who/what answered it)
- May include summary of which answers resolved the question
- Both AI and humans can propose closure
