---
id: seeds-74
title: Link seeds to source conversations for retrospective analysis
status: captured
type: idea
created_at: 2026-02-06T21:33:07.829797+00:00
updated_at: 2026-03-11T20:50:19.704043+00:00
tags:
  - workflow
  - meta
relationships:
  - target_id: seeds-115
    rel_type: relates-to
    created_at: 2026-02-06T21:33:07.829797+00:00
  - target_id: seeds-75
    rel_type: questioned-by
    created_at: 2026-02-06T21:33:19.955697+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Observation: When using seeds across projects, sometimes the captured seeds don't adequately capture all details about an investigation or decision.

**Problem:**
- Seeds are snapshots that may miss nuance from the original conversation
- Hard to go back and see what context led to a seed
- Can't evaluate whether a seed accurately represents the discussion

**Potential approaches:**
- Store conversation excerpts or timestamps with seeds
- Link to Claude Code conversation exports
- Add a 'source' field for referencing external context
- Periodic review workflow: compare seeds against source conversations

**Questions:**
- What format do conversation exports take?
- How to link without bloating the seed data?
- Is this about better capture at creation time, or retrospective review?
