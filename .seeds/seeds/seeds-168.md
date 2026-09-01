---
id: seeds-168
title: "Idea: position seeds as UPSTREAM of intent — the journey that produces it, including discarded paths"
status: exploring
type: idea
created_at: 2026-06-15T22:01:59.051112+00:00
updated_at: 2026-08-31T20:02:42.565858+00:00
tags:
  - positioning
  - framing
  - deliberation
  - intent
  - journey
relationships:
  - target_id: seeds-167
    rel_type: relates-to
    created_at: 2026-06-15T22:02:27.390141+00:00
  - target_id: seeds-101
    rel_type: relates-to
    created_at: 2026-06-15T22:02:27.524526+00:00
  - target_id: seeds-175
    rel_type: relates-to
    created_at: 2026-06-17T16:41:24.886330+00:00
  - target_id: seeds-176
    rel_type: relates-to
    created_at: 2026-06-17T16:41:25.002201+00:00
  - target_id: seeds-176.1
    rel_type: relates-to
    created_at: 2026-06-17T18:14:42.597462+00:00
  - target_id: seeds-176.2
    rel_type: relates-to
    created_at: 2026-06-17T18:21:04.787250+00:00
  - target_id: seeds-176.5
    rel_type: relates-to
    created_at: 2026-06-18T22:32:21.685134+00:00
  - target_id: seeds-176.6
    rel_type: relates-to
    created_at: 2026-06-18T22:32:21.803480+00:00
  - target_id: seeds-176.8
    rel_type: relates-to
    created_at: 2026-06-18T22:32:22.581481+00:00
  - target_id: seeds-189
    rel_type: relates-to
    created_at: 2026-07-09T22:42:02.158956+00:00
  - target_id: seeds-190
    rel_type: relates-to
    created_at: 2026-07-09T22:42:02.607785+00:00
  - target_id: seeds-196
    rel_type: relates-to
    created_at: 2026-07-14T17:06:38.946062+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

The inverse of the declined intent-debt-vocabulary boundary (see that seed). seeds *does* capture intent — but what it really captures is the **journey to reaching intent**, and that journey is, to @aguynamedryan, just as valuable as the destination. Intent is a *byproduct* of deliberation: "you don't figure out what you're trying to do until you've talked about and deliberated what you're trying to do."

What the intent-debt framing structurally omits, and seeds keeps:
- **What was considered and discarded**, and *why* — so you don't revisit a dismissed idea thinking it's new, and you remember why you dismissed it.
- **Why decisions changed** — "why did a guard clause get put in, and why did it get taken back out? what happened in the 2023 incident that changed hearts and minds, and what other resolutions were considered?" None of that is intent; it's the deliberation around intent.

Intent is also *fractal*: you can hold an intent while the way you achieve it stays open, and each sub-decision has its own intent underneath it ("my intention with seeds is to capture deliberation, but the way I've gone about it is a series of other decisions, each with its own intent"). seeds should capture each layer.

This is a positioning / README / blog direction, not a code change — the sharpest single line from the intent-debt review: seeds is *upstream of* intent, not intent-debt tooling. Relates to seeds-101 (landscape research) and seeds-107 (acknowledgments).

Status: exploring — the active direction @aguynamedryan is articulating.



---
## 2026-06-18 — precision: "upstream of INTENT," not "upstream of everything"

@aguynamedryan correction (verbatim-ish): "I never said seeds is upstream of EVERYTHING else — that was your [the assistant's] assertion." Guard the framing: the claim is that seeds is upstream of INTENT (the journey that produces it). Do NOT inflate it to "upstream of everyone/everything," "everyone else is downstream," or "seeds is the only one that keeps the journey." Those totalizing claims are false and were the assistant's over-reach: intent.build reaches upstream too (its Arena surface), and DeltaDB keeps a (downstream) journey of its own. The honest distinction is not lifecycle position but what a tool makes FIRST-CLASS — seeds foregrounds the deliberation/journey; the others foreground the decision or the code. Keep the positioning precise and non-totalizing in the post. (See seeds-176.5 intent.build, seeds-176.2 DeltaDB.)
