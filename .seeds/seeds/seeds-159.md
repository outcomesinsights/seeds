---
id: seeds-159
title: "Concern: resolved deliberation can go stale — staleness AND contradiction among resolved seeds"
status: resolved
type: concern
created_at: 2026-06-15T21:58:55.309000+00:00
updated_at: 2026-09-01T16:59:33.636334+00:00
resolved_at: 2026-09-01T16:59:33.636325+00:00
tags:
  - lifecycle
  - decay
  - staleness
  - contradiction
  - resolution-audit
  - intent-debt
  - winnow
  - 2026-09-01
relationships:
  - target_id: seeds-158
    rel_type: relates-to
    created_at: 2026-06-15T22:00:37.959928+00:00
  - target_id: seeds-160
    rel_type: relates-to
    created_at: 2026-06-15T22:00:38.355202+00:00
  - target_id: seeds-161
    rel_type: relates-to
    created_at: 2026-06-15T22:00:38.645431+00:00
  - target_id: seeds-164
    rel_type: questioned-by
    created_at: 2026-06-15T22:00:39.038979+00:00
  - target_id: seeds-187
    rel_type: relates-to
    created_at: 2026-06-24T17:55:16.155753+00:00
  - target_id: seeds-74.2
    rel_type: relates-to
    created_at: 2026-09-01T16:58:33.623178+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

seeds preserves the journey, but a resolution captured months ago rests on premises — data shape, library versions, constraints, team priorities — that may since have changed. Today the only correction is reactive and manual: a resolved seed gets reopened because reality disagreed (seeds-7). There is no concept of a resolution *aging out* — nor of two resolutions *contradicting* each other.

Two detection targets @aguynamedryan named (2026-06-15):
1. **Aged-out premises** — a resolution whose basis no longer holds.
2. **Downstream contradiction / cognitive dissonance** — "go through resolved seeds and pull out any that look like they've been contradicted downstream by others marked resolved or captured." Did we resolve one thing two months ago and resolve something contradicting it a week ago?

The field names the first directly: Meta's tribal-knowledge work warns "context that decays is worse than no context at all" and re-validates on a schedule; Storey's intent-debt framing treats externalized rationale as something that *erodes*.

The hard part — and the attached open question — is detection: what guidance do you give an agent so it knows which kinds of resolutions to question, and how do we surface candidates for review?

This is one flavor of the broader seeds self-audit / consistency-check family (see the umbrella seed), and a cousin of the retrospective-outcome and learning-capture seeds.

Distinct from seeds-50 (coherence/story of the live graph, not freshness) and seeds-131 (re-gleaning source inputs, not re-validating resolutions).

Status: deferred — interesting, not actively pursuing; a free-afternoon meditation. Risk: seeds is journey-capture, not a freshness monitor; a lightweight revisit / flag-contradiction affordance may be all that fits, not a decay-detection engine.


---

## RESOLVED 2026-09-01. Detection answered; shipping as `winnow` (see seeds-158).

This seed deferred on one thing: *"The hard part — and the attached open question — is
detection: what guidance do you give an agent so it knows which kinds of resolutions to
question, and how do we surface candidates for review?"*

Answered in seeds-164: **scope detection to the graph, not the corpus.** Contradiction
requires two seeds to be about the same thing, and the parent/child hierarchy plus
`relates-to` edges already encode exactly that. The candidate set is the edge set — 692
edges, not ~49,000 pairs (measured 2026-09-01). The unit of review is an edge, not a seed.

Both detection targets named above are covered:

1. **Aged-out premises** — but sharpened. Target resolved seeds that cite a *checkable*
   fact (a version, a measurement, a data shape), not seeds that are merely old. Age alone
   is not evidence of staleness, and treating it as such is how this becomes the
   decay-detection engine this seed rightly feared.
2. **Downstream contradiction** — walk edges, compare endpoints where both are resolved or
   where one was resolved and the other captured later.

**The risk recorded above was the right one and it is preserved as a design constraint, not
dissolved.** This seed warned: *"seeds is journey-capture, not a freshness monitor; a
lightweight revisit / flag-contradiction affordance may be all that fits, not a
decay-detection engine."* Ryan ruled 2026-09-01 for the full five-flavor scope, so the
guard moved from scope into shape — hard findings separated from soft, every finding
required to cite its evidence, and the detector itself tested on hand-built fixtures
including a pair that only *looks* like a contradiction. See seeds-158 for the full
guardrail set.

**Worked proof case, produced the same day.** Draining seeds-74.2 surfaced exactly the
failure this seed predicted: seeds-74.2.2 concluded gleaning should analyse the model's own
context; seeds-74.2.1 later proved that cannot work post-compaction. Two children of one
parent, contradicting each other, unreconciled for roughly six months because nothing
forced a pass over the cluster. This seed was right that it happens, and right that
detection was the obstacle.
