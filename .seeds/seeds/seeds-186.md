---
id: seeds-186
title: Intent-capture guidance for the seeds-to-beads skill (provisional)
status: captured
type: idea
created_at: 2026-06-24T16:47:31.541835+00:00
updated_at: 2026-06-24T16:47:31.541843+00:00
tags:
  - intent
  - seeds-to-beads
  - skill
  - beads
relationships:
  - target_id: seeds-184
    rel_type: relates-to
    created_at: 2026-06-24T16:47:32.010657+00:00
  - target_id: seeds-152.4
    rel_type: relates-to
    created_at: 2026-06-24T16:47:32.139471+00:00
  - target_id: seeds-w42l
    rel_type: relates-to
    created_at: 2026-08-27T14:19:32.082752+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Feedback distilled from the intent investigation (linked): the seeds-to-beads skill should tell the converter to capture intent for the EXECUTOR, not just provenance. When present in the deliberation, each bead should record:
- Locked decisions + their rationale -- stops the executing agent re-litigating a settled call.
- Stakeholder voice on subjective / taste / scope calls, quoted verbatim.
- Seed lineage (Source: seeds-NNN).
Plus: separate motivation (why do it) from constraints (what's already decided); keep it proportional to the bead's weight.

PROVISIONAL: popped into src/seeds/plugin/claude-plugin/skills/seeds-to-beads/SKILL.md now so the thinking is not lost. Likely to be retooled after the broader efficacy/metrics discussion settles (see the open question on the linked investigation). The "which intent format is most effective" ranking is reasoned, not measured -- treat it as a hypothesis, not a finding. Extends the skill work in seeds-152.4 and the handoff design in seeds-12.4.
