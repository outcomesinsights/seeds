---
id: seeds-161
title: "Concern: seeds captures the prescriptive journey well but under-captures what we LEARNED by trying"
status: deferred
type: concern
created_at: 2026-06-15T21:58:55.600505+00:00
updated_at: 2026-09-01T16:58:50.500502+00:00
tags:
  - learning
  - lifecycle
  - capture-gap
  - resolution-audit
  - winnow
relationships:
  - target_id: seeds-158
    rel_type: relates-to
    created_at: 2026-06-15T22:00:38.202922+00:00
  - target_id: seeds-160
    rel_type: relates-to
    created_at: 2026-06-15T22:00:38.506317+00:00
  - target_id: seeds-159
    rel_type: relates-to
    created_at: 2026-06-15T22:00:38.645431+00:00
  - target_id: seeds-184
    rel_type: relates-to
    created_at: 2026-06-24T16:47:31.797077+00:00
  - target_id: seeds-187
    rel_type: relates-to
    created_at: 2026-06-24T17:55:16.026564+00:00
  - target_id: seeds-193
    rel_type: relates-to
    created_at: 2026-07-10T17:17:20.671756+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

@aguynamedryan's own admission, reviewing the intent-debt landscape (2026-06-15): "I'm not capturing learning as much as I'd like. That's a very interesting point." seeds is strong on the *prescriptive* phase — plant the idea, explore it in the abstract, get concrete about applying it to the system (the gardening metaphor: planting is prescriptive). It is weaker at capturing what we *learned* after an idea was actually tried — the discoveries, the insights, the places an approach failed and why it changed.

The honest nuance that softens the gap: a lot of the learning already happens *in the deliberation itself*, and by implementation time @aguynamedryan usually has a firm handle on what he wants. He has rarely needed to revisit an implementation decision, because so far they have stood by the decisions made — "I'm not claiming perfect software; we'll see how that plays out." So the gap is real but not yet painful.

This is the third cousin in the seeds self-audit family (see the umbrella seed), with the staleness-audit and retrospective-outcome seeds. They may collapse into one mechanism: a way for seeds to look back over its own resolved deliberation and ask what aged out, what contradicts what, what panned out, and what we learned.

Status: deferred — note it alongside the other two; revisit on a free afternoon to see if a concrete shape sparks.



---
**2026-09-01: partially absorbed by `winnow` (seeds-158).** Ryan ruled the corpus-audit skill covers all five flavors of the self-audit family, this one included — so the *surfacing* half now has a home and a shape. What `winnow` can do here is bounded: neither outcome nor learning is detectable from the corpus alone, so both are surfaced as prompts for the user to answer, never asserted by the tool (see seeds-164). The broader concern in this seed — that seeds under-captures this material at resolution time, not just at audit time — is NOT addressed by winnow and stays live here. Cousin: the `resolve-seeds-from-beads` skill already carries learnings back at resolution time.
