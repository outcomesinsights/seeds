---
id: seeds-158
title: Should seeds audit its own body of knowledge? A self-consistency / sanity-check family
status: exploring
type: question
created_at: 2026-06-15T21:58:55.152165+00:00
updated_at: 2026-08-31T20:02:41.750970+00:00
tags:
  - self-audit
  - consistency
  - sanity-check
  - resolution-audit
  - corpus
  - meta
relationships:
  - target_id: seeds-159
    rel_type: relates-to
    created_at: 2026-06-15T22:00:37.959928+00:00
  - target_id: seeds-160
    rel_type: relates-to
    created_at: 2026-06-15T22:00:38.085326+00:00
  - target_id: seeds-161
    rel_type: relates-to
    created_at: 2026-06-15T22:00:38.202922+00:00
  - target_id: seeds-162
    rel_type: questioned-by
    created_at: 2026-06-15T22:00:38.777316+00:00
  - target_id: seeds-163
    rel_type: questioned-by
    created_at: 2026-06-15T22:00:38.902502+00:00
  - target_id: seeds-175.8
    rel_type: relates-to
    created_at: 2026-06-17T16:41:25.466085+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Reviewing the cousin cluster (staleness, retrospective-outcome, learning-capture), @aguynamedryan zoomed out to the umbrella they are all instances of (2026-06-15): beyond operational maintenance (clean indexes, healthy DB — what `doctor` does), is there a *semantic* maintenance — can seeds keep its own **body of knowledge consistent and up to date** by auditing itself?

Named flavors of the audit, in his words:
- **Staleness** — resolutions whose premises (data shape, versions, constraints, priorities) have since changed and may no longer hold.
- **Cognitive dissonance / contradiction among resolved seeds** — "did we resolve one thing two months ago, and resolve something that contradicts it a week ago?" Surface resolved seeds that disagree with each other. The sharpest new flavor.
- **Outcome** — did a resolved decision actually pan out?
- **Learning** — are we capturing what we learned by trying, not just what we decided?
- **Neglected deferrals** — "are there deferred things falling through the cracks?" Surface deferred seeds that have gone quiet and may deserve another look.

"These are all questions we could make of seeds, and it would be able to" answer them ad hoc today. The real open question is whether to **formalize them as first-class tools/commands** — a `seeds audit` / `seeds check` family — versus leaving them as things an agent does on request. (Attached as questions.)

Distinct from `doctor` (operational health) and seeds-50 (story-coherence of the live graph). This is consistency-and-freshness of the *resolved* knowledge body. The three cousin seeds relate to this umbrella.

Status: exploring — actively deliberated; the specific mechanisms (the cousins) remain deferred until a shape sparks.
