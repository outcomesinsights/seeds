---
id: seeds-152.2
title: "Decision: skills shipped with seeds are prompt-macro scale, not workflow engines"
status: captured
type: decision
parent: seeds-152
created_at: 2026-05-27T18:22:43.163221+00:00
updated_at: 2026-05-27T18:22:43.163230+00:00
tags:
  - scope
  - skills
  - design
  - calibration
relationships:
  - target_id: seeds-151.2
    rel_type: relates-to
    created_at: 2026-05-27T18:30:59.836639+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Calibration that emerged from a misaligned exchange: an agent (me) responded to a "should we ship skills?" question by sketching workflow engines with confirmation gates, data-model thinking, and persona considerations. The user clarified that they meant something much smaller — prompt-macro-scale skills, 3–10 lines of markdown.

## The decision

Skills shipped with seeds are **prompt macros**, not workflow engines. Each skill is a small markdown file that prepends or frames the user's next utterance. No multi-step orchestration. No confirmation gates. No data-model logic embedded in the skill itself.

## Why

- **Cheap to ship.** A 3-line skill can be added in minutes and revised at no cost.
- **Cheap to iterate.** If a phrase isn't working, edit the markdown — no code change.
- **Cheap to discard.** Skills that don't earn their keep cost nothing to remove.
- **The closer pattern proves the value of small.** A single line ("invite questions/comments/criticisms") carries real behavioral weight (see [[agents-under-surface-doubts-unless-invited]]). Skills don't need to be large to matter.
- **Workflow engines are premature commitment.** We don't yet know which workflows are worth automating. Building infrastructure before discovering the need is the textbook scope-creep failure mode.

## What fits this scope

- `feedback` — frames the next utterance as feedback on the prior turn, with the closer baked in
- `closure-check` — asks the agent to list what *it* believes is unresolved (never to declare resolution; see [[risk-lodestones-may-over-channel-agent-reasoning]])
- `utterance-ingest` (seeds-152.1) — frames the next utterance as raw material for seed creation/update, with a confirmation gate

## What doesn't (yet)

- `seeds-to-beads` with full conversion logic and confirmation gates — this is workflow-engine scale and should be deferred until the prompt-macro skills are in use and the friction point is concrete.
- Persona agents (Cedric) — see seeds-152; only after we have enough skills to notice a shared voice.

## Reversibility

If we accumulate a critical mass of prompt-macro skills that clearly want to be fatter, this decision can be revisited. For now, "macro until proven otherwise" is the posture.
