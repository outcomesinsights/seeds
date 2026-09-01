---
id: seeds-173
title: In implementation session logs, does an agent actually follow a reference back to a seed?
status: resolved
type: question
created_at: 2026-06-15T22:02:28.324462+00:00
updated_at: 2026-08-31T20:02:42.914850+00:00
resolved_at: 2026-06-15T22:09:06.799734+00:00
relationships:
  - target_id: seeds-169
    rel_type: questions
    created_at: 2026-06-15T22:02:28.327605+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Not guaranteed — and by design it may not need to be. The bead-process skill (the implementer's playbook) contains NO instruction to read the cited seed; the implementing Sonnet agent works from the self-contained bead, and the "Source:" citation is an explicit "might need" fallback rather than the primary channel. Transcript evidence is inconclusive: this project's main session transcripts show ~40 "seeds show seeds-N" and ~221 "seeds prime" invocations, but those are predominantly DELIBERATION sessions (an agent looking seeds up while thinking with @aguynamedryan), not implementers — the bead-process implementers run in throwaway worktrees whose transcripts do not surface in the project session directory. Net conclusion: the implementer is fed distilled intent through the bead and rarely needs to dereference the seed, which matches @aguynamedryan's goal that an agent should not have to figure out what to do because that is solved before it is told to implement.
