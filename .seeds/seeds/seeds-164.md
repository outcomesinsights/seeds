---
id: seeds-164
title: How do we detect candidates for review — what guidance tells an agent which resolved seeds to question for staleness or contradiction?
status: resolved
type: question
created_at: 2026-06-15T22:00:39.035499+00:00
updated_at: 2026-09-01T16:57:57.256350+00:00
resolved_at: 2026-09-01T16:57:57.256344+00:00
relationships:
  - target_id: seeds-159
    rel_type: questions
    created_at: 2026-06-15T22:00:39.038979+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

**Answered 2026-09-01. Scope detection to the graph, not the corpus.**

This question blocked seeds-158 and seeds-159 from June 2026 because detection looked
open-ended: how would an agent know *which* of 314 resolved seeds to question? Pairwise
comparison is ~49,000 pairs and absurd, and unguided sampling would produce noise.

The answer came from a worked case rather than from theory. On 2026-09-01, draining the
seeds-74.2 cluster surfaced a genuine six-month-old contradiction: seeds-74.2.2 concluded
that gleaning should analyse the model's own conversational context, while seeds-74.2.1's
later section proved that cannot work post-compaction. Both were children of the same
parent.

**That is the detection rule: contradictions live inside clusters, not across the corpus.**

Contradiction requires two seeds to be *about the same thing*, and "about the same thing"
is precisely what the parent/child hierarchy and `relates-to` edges already encode. So the
candidate set is not the cross product of seeds — it is the edge set. Measured 2026-09-01:
314 seeds, 692 edges. Detection is bounded by ~692 comparisons, not ~49,000, and every
comparison is between two seeds already asserted to be related.

Corollary worth stating: an edge is the *unit of review*, not a seed. Asking "is this seed
stale?" in isolation has no reference point; asking "do these two related seeds still agree,
and does the older one still hold given the newer?" does.

**Per-flavor detection, following from the same principle:**

- **Contradiction** — walk edges; compare the two endpoints where both are resolved, or one
  resolved and one captured later. Bounded, and this is the flavor with a proof case.
- **Neglected deferrals / long-unresolved** — purely mechanical. Status plus dates plus
  graph position (deferred and quiet, or blocked with all blockers closed). No judgment
  needed, so it belongs in a tested verb.
- **Staleness** — a resolved seed whose *premises* are stated and checkable (a version, a
  measurement, a data shape). Detection targets seeds that cite a checkable fact, not seeds
  that are merely old. Age alone is not evidence of staleness and must not be treated as
  such.
- **Outcome** — cannot be detected from the corpus at all; it requires knowing what happened
  downstream. Surfaced for the user to answer, never asserted.
- **Learning** — same: a prompt for the user, not a detection.

**Guardrail this answer implies.** The flavors have very different confidence. Mechanical
findings (dates, graph state) are facts; staleness and outcome are guesses. They must be
reported separately so a soft-flavor false positive does not discredit the hard findings —
a corpus auditor that cries wolf is worse than none, because it trains the reader to skip
it. Every finding cites the specific seed IDs and the specific conflicting text; a finding
that cannot cite is not reported.

Implemented as `winnow` (Ryan, 2026-09-01) — see seeds-158.
