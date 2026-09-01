---
id: seeds-146
title: Does seeds need a glossary mechanism for communicating actual-vs-pending writes?
status: captured
type: question
created_at: 2026-05-21T18:36:16.793988+00:00
updated_at: 2026-08-31T20:02:41.040897+00:00
tags:
  - glossary
  - ai-ux
  - convention
  - prime
  - communication
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Open question surfaced during code_set_catalog session 2026-05-21.

During a planning conversation about a feature, the AI wrote "Promotion Playbook Push-back — Captured" as a section header. @aguynamedryan read "captured" and inferred a seed had been written. The agent had only meant "I heard you in this conversation; no seed write yet." Misread led to confusion about what state the seed graph was actually in.

@aguynamedryan's framing (paraphrased):
> "We probably need to maintain a glossary for what we should say when we are doing planning, for us to give indications about what is actually happening behind the scenes with seeds."

The pragmatic glossary the agent proposed and adopted in that session:

| Phrase | State |
|---|---|
| Filed/Wrote/Created csc-X | Durable change made. Seed exists / has been edited. |
| Updated/Resolved/Deferred csc-X | Durable change made. |
| Drafting csc-X / Writing csc-X now | About to make the change in this turn. |
| Will file… / Queued (no ID) | Intended, not done. Waiting. |
| Noted / Acknowledged / Captured (no ID) | Conversation only. No seed write. |
| Locked in / Confirmed (no creation verb) | Converged in dialogue, not written. |

Rule of thumb: past-tense verb with a concrete ID = durable; anything without an ID = conversation only.

The question for seeds:
- Should seeds itself carry a glossary as a first-class concept (versioned, prime-able, shareable across projects)?
- Where does it live — alongside the project, baked into seeds prime output, agents-facing only, human-readable too?
- Is the glossary scope per-project or cross-cutting (seeds-tool-wide)?
- Does it need to vary by agent (a Claude glossary, a Codex glossary), or is one shared glossary sufficient?
- Could it be a project-level config file (.seeds/glossary.toml or similar) that seeds prime surfaces?

Related: seeds-21 (AI natural adoption — make tool intuitive for AI), seeds-143 (prime guidance: describe primitives not prescribe workflows), seeds-130 (project-aware gleaning).
