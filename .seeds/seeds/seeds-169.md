---
id: seeds-169
title: "Question: do agents actually consume seeds? Trace whether seed intent reaches the beads/agents that implement"
status: resolved
type: question
created_at: 2026-06-15T22:01:59.182458+00:00
updated_at: 2026-08-31T20:02:42.685461+00:00
resolved_at: 2026-06-15T22:19:09.776493+00:00
resolution: "Yes — but intent reaches the implementer through the distilled, self-contained bead, not by the agent reading seeds. Beads cite their source seeds by convention (~37/83 carry a \"Source: seeds-X\" line, skill-mandated), and intent carries in distilled form (bead = \"## Why\" + pre-written content; the journey stays in the seed). The implementer is NOT told to dereference the citation — the bead-process skill never mentions seeds — so the seed is upstream / distillation-time context, not a live lookup. This is exactly the goal: the seeds->beads conversion front-loads the figuring-out so the agent does not have to. The dependency it exposes: hand-off quality rides entirely on the distillation step. Full findings are in the seed body plus answered sub-questions seeds-171 / seeds-172 / seeds-173."
tags:
  - beads-integration
  - agent-context
  - verification
  - provenance
  - investigation
relationships:
  - target_id: seeds-87
    rel_type: relates-to
    created_at: 2026-06-15T22:02:27.668195+00:00
  - target_id: seeds-85
    rel_type: relates-to
    created_at: 2026-06-15T22:02:27.789392+00:00
  - target_id: seeds-171
    rel_type: questioned-by
    created_at: 2026-06-15T22:02:28.044032+00:00
  - target_id: seeds-172
    rel_type: questioned-by
    created_at: 2026-06-15T22:02:28.182238+00:00
  - target_id: seeds-173
    rel_type: questioned-by
    created_at: 2026-06-15T22:02:28.327605+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

@aguynamedryan does not know whether seeds actually provides context to the agents that implement features. He has not looked, because he has been one-shotting features and "haven't felt the need to look under the hood at what's causing the magic." The intent-debt landscape keeps emphasizing intent-as-context-for-an-agent, and that has not been a focus of seeds — so it is worth checking, *inside seeds* (per @aguynamedryan: "why would we do the investigation outside of seeds? the whole point is we're supposed to be doing things inside of seeds").

The investigation, three sub-questions (attached):
1. Do the beads generated from a seed reference the seed they came from?
2. When a seed becomes beads, does the seed's intent carry into the bead description — or is it lost in the hand-off?
3. In implementation session logs, does an agent actually follow a reference back to a seed?

Why it matters: it tells us whether "the audience is the agent" is real for this workflow. @aguynamedryan's goal is that an agent should *never* have to figure out what it's supposed to do — that is solved in deliberation *before* the bead is handed off. So the question is whether the intent worked out in a seed is reaching the implementer at all, or whether the magic is coming from somewhere else.

Relates to seeds-85 (MCP vs better CLI integration) and seeds-87 (dynamic prime — injecting live deliberation state into agent context).

Status: exploring — investigation pending (this session).



---
INVESTIGATION FINDINGS (2026-06-15): Intent DOES reach the implementer — but through the distilled, self-contained bead, not by the agent reading seeds.
1. Beads cite their source seeds by convention (skill-mandated; ~37/83 beads carry a "Source: seeds-X" line).
2. Intent carries in distilled form: the bead holds a "## Why" + pre-written content while the full journey stays in the seed ("Beads represent work; seeds carry the deliberation").
3. The implementer is NOT told to dereference the citation — the bead-process skill never mentions seeds — so the seed is upstream / distillation-time context, not a live lookup.

This is the "magic": the seeds->beads conversion front-loads the figuring-out so the implementer does not have to. It reinforces the "seeds is upstream of intent" thesis and exposes a real dependency — hand-off quality rides entirely on the distillation step (ties to the learning-capture and reasoning-compression seeds). Open follow-up: should the implementer optionally pull the cited seed when a bead is underspecified, or does that fight the self-contained-bead design? The three sub-questions are answered individually.
