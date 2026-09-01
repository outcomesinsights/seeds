---
id: seeds-20
title: "Explicit vs possible relationships: confirmed vs AI-suggested"
status: deferred
type: idea
created_at: 2026-01-28T05:56:22.814297+00:00
updated_at: 2026-01-28T17:19:20.678912+00:00
tags:
  - model
  - ai-ux
relationships:
  - target_id: seeds-6
    rel_type: relates-to
    created_at: 2026-01-28T05:54:02.752699+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

From spec_first_pass.md:

User envisions distinguishing between:
- Explicitly related: User or AI has confirmed the relationship
- Possibly related: AI suggests a potential connection

This distinction could be a helpful signal to both humans and AI.

Additional notes:
- Declaring seeds as unrelated doesn't make them 'standalone forever'
- A new seed introduced later might create a relationship
- No seed is ever truly declared permanently standalone
