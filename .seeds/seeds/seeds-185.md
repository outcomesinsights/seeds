---
id: seeds-185
title: Should seeds instrument the efficacy of generated beads, and if so what/how?
status: captured
type: question
created_at: 2026-06-24T16:47:31.390914+00:00
updated_at: 2026-08-31T20:02:45.579136+00:00
tags:
  - metrics
  - efficacy
  - beads
  - intent
relationships:
  - target_id: seeds-184
    rel_type: questioned-by
    created_at: 2026-06-24T16:47:31.691257+00:00
  - target_id: seeds-187
    rel_type: relates-to
    created_at: 2026-06-24T17:55:16.265161+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Genuinely undecided -- capturing the deliberation, not a decision.

PROPOSAL on the table: at seed resolution, the agent writes a short HONEST efficacy note for the beads that implemented it -- did they need meaningful tweaking? was a tweak a planning miss (a better bead would have caught it) or an inherent unknown only discoverable by building? what would the better bead have said? Qualitative, low-friction, and nearly free because the agent is already present at resolution.

WHERE it could live:
- On the bead: beads IS extensible -- `bd create --metadata '<json>'` (arbitrary JSON) plus labels/tags/set-state. Technically viable, but an unschemaed blob in the ephemeral bead world we do not own.
- On the seed resolution (preferred): seeds is ours end-to-end; the seed is the durable artifact; and the honest assessment can only be made post-implementation, which is exactly when we resolve.

STANCE to weigh: capture-first, quantify-later. Do not metricize a nebulous qualitative process before we understand its shape -- accumulate structured qualitative resolution notes, then see whether a worth-counting pattern emerges. @aguynamedryan is ambivalent ("not sure I want it"; measurement isn't his historical forte); the counter is that AI is a better, more consistent record-keeper than we have been, so the capture cost is now low. Even perfect capture will not yield causal attribution (did better intent CAUSE better implementation) -- and that is fine; the aim is a searchable record of where planning missed, not a dashboard. Relates to seeds-161.
