---
id: seeds-7
title: "AI role: participant vs facilitator in deliberation?"
status: captured
type: question
created_at: 2026-01-28T05:54:10.099256+00:00
updated_at: 2026-03-11T20:50:17.459504+00:00
tags:
  - ai-ux
  - philosophy
relationships:
  - target_id: seeds-117
    rel_type: relates-to
    created_at: 2026-01-28T05:54:10.099256+00:00
  - target_id: seeds-190
    rel_type: relates-to
    created_at: 2026-07-09T22:42:02.730193+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

From spec_first_pass.md: AI can:
- Research and answer questions
- Propose relationships between seeds
- Suggest closure for questions
- Extract seeds from transcripts
- Propose that seeds might belong to a topic

From the 'what language' example: 'AI had made a decision. Decision was made.' - AI appears to be a legitimate decision-maker in some contexts.

Key tension: seeds differs from Beads in audience:
- Beads: Primarily for AI internal bookkeeping, somewhat user-facing
- seeds: For humans to use in their bookkeeping, assisted by AI which also uses it for its bookkeeping

This dual nature creates design tension: tool must be intuitive for humans AND easily adopted by AI agents.



---
**Specific AI behaviors observed/desired (consolidated from seed-757a, seed-1c5e, seed-033a):**

**Positive pattern (from seed-757a):**
AI suggesting status changes during conversation feels like natural collaboration - draws attention to next steps.

**Design ideas (from seed-1c5e, seed-033a):**
- Conversational feedback should flow into seeds - AI should recognize when to capture insights
- AI should propose triage/organization rather than asking user to do it - reduces cognitive load

These suggest AI as active *participant* who proposes and acts, not just passive facilitator who waits for instructions.
