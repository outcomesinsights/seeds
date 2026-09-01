---
id: seeds-124
title: "Relationship type discovery: organic refinement of relates-to edges"
status: captured
type: decision
created_at: 2026-03-12T15:19:16.241102+00:00
updated_at: 2026-03-12T15:19:27.656883+00:00
tags:
  - model
  - workflow
relationships:
  - target_id: seeds-6
    rel_type: relates-to
    created_at: 2026-01-28T05:54:02.752699+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Decision: new relationship types are discovered organically, not defined speculatively.

Process:
1. Use relates-to by default when linking seeds
2. Periodically review relates-to edges for recurring patterns
3. When a pattern is clear, name it and add to the RelationType enum

relates-to is explicitly a triage signal — it means 'these are related but we haven't identified the specific relationship yet.' It's not a permanent category.

Initial types: questions, answers, relates-to. Future candidates observed in production data: decision-addresses-idea, concern-about, explores.
