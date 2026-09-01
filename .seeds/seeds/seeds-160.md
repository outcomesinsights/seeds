---
id: seeds-160
title: "Idea: retrospective outcome — did the resolved decision actually pan out?"
status: deferred
type: idea
created_at: 2026-06-15T21:58:55.455330+00:00
updated_at: 2026-08-31T20:02:41.994747+00:00
tags:
  - lifecycle
  - outcome
  - retrospective
  - feedback-loop
  - resolution-audit
relationships:
  - target_id: seeds-158
    rel_type: relates-to
    created_at: 2026-06-15T22:00:38.085326+00:00
  - target_id: seeds-159
    rel_type: relates-to
    created_at: 2026-06-15T22:00:38.355202+00:00
  - target_id: seeds-161
    rel_type: relates-to
    created_at: 2026-06-15T22:00:38.506317+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

seeds captures the resolution *at close* (seeds-134) and links experiments that *inform* a decision before it is made (seeds-115), but nothing revisits a resolved decision *afterward* to record whether it held up in production. The decision-journal field (Yorick) makes the point worth stealing: separate *decision quality* from *outcome luck* — a good decision can have a bad outcome and vice versa, and you only learn which by looking back.

@aguynamedryan's stance (2026-06-15): genuinely interesting, and a cousin of the staleness-audit and learning-capture seeds — one instance of the seeds self-audit family (see the umbrella seed). If there is ever a resolution audit, it could surface both "this may no longer apply" and "here is how it panned out" together. But there is a real adoption worry, in his words: "how am I gonna be motivated to actually slog my way through that? It feels like a heavy chore with questionable relevance and questionable value." Not pressing — a nice-to-have, or something a user with a different goal for the tool might want. Not opposed; not clamoring for it.

Open shape: a light "revisit" affordance on resolved seeds, and/or an optional `outcome` field distinct from `resolution` ("resolution = what we decided; outcome = how it actually turned out"). Keep it optional and agent-surfaced — @aguynamedryan never runs the CLI, so it cannot depend on him remembering to revisit. Partly overlaps seeds-115 (experiment outcomes *before* the decision); this is the *post*-resolution, in-production variant.

Status: deferred (cousin cluster).
