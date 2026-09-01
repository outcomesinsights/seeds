---
id: seeds-w42l
title: seeds-to-beads should consult the user on unsettled decisions by default; --autonomous opts out
status: captured
type: decision
created_at: 2026-08-27T14:19:28.116443+00:00
updated_at: 2026-08-31T20:02:50.202204+00:00
tags:
  - skill
  - seeds-to-beads
  - beads
  - intent
  - consultation
  - autonomous
  - 2026-08-27
relationships:
  - target_id: seeds-152.4
    rel_type: relates-to
    created_at: 2026-08-27T14:19:31.963845+00:00
  - target_id: seeds-186
    rel_type: relates-to
    created_at: 2026-08-27T14:19:32.082752+00:00
  - target_id: seeds-184
    rel_type: relates-to
    created_at: 2026-08-27T14:19:32.196272+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

The seeds-to-beads skill converted in one pass: it made every call the deliberation had left open, silently, and handed the result to an executing agent that could not ask either. @aguynamedryan's ruling flips the default.

Verbatim:

> "as beads are being generated, if the process surfaces decisions to be made that would benefit from user input, the skill should prompt the user before making the bead so the bead has complete input from the user"

> "I'd like to add a flag for 'autonomous' where the current behavior of just plunging on ahead seems to be the norm"

## The decision

Consulting is the default; one-pass conversion is opt-in via --autonomous.

The timing matters and is the whole point: ask BEFORE the bead is written, not after. A question costs a sentence. A bead that ships with a guess baked into it costs a round of rework, and the guess is invisible by the time it costs anything -- it reads as a settled decision to the executing agent.

## The bar for asking

The risk is an interrogation, which would make the skill worse than plunging ahead. Ask only where the decision is genuinely the user's:
- scope boundary (this bead / separate bead / out of scope)
- taste, UX, naming -- anything landing on a surface a person reads
- something the seeds raised and never landed, or two seeds pointing different directions
- acceptance criteria that need a definition picked before they can be mechanical
- sequencing that encodes a design commitment rather than an ordering convenience

Explicitly do NOT ask about: anything the deliberation already settled (re-opening a locked decision is the failure this skill exists to prevent -- see the locked-decisions guidance in [[seeds-186]]), mechanical decomposition and wording, or anything answerable by reading the repo.

Batch the questions after a full analysis pass rather than dripping them one at a time; offer options with a recommendation so a one-word answer is complete.

## Autonomous is not silent

--autonomous restores the prior behavior, but every call it would otherwise have asked about is recorded in the bead as an explicit assumption (\"Assumed: ... -- the deliberation didn't settle this\") and gathered into the closing summary. The judgment stays visible and overturnable without reading every bead to find it.

## Feedback loop back into seeds

When an answer settles something the originating seed had open, carry it back with seeds answer / a note on the seed. Otherwise the deliberation record ends up poorer than the beads it produced -- which inverts the point of the tool.

Extends the skill defined in [[seeds-152.4]] and the intent-capture guidance in [[seeds-186]]; feeds the efficacy question in [[seeds-184]], since consultation should shift \"tweaking needed\" from planning-miss toward inherent-unknown.
