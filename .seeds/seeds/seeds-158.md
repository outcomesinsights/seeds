---
id: seeds-158
title: "Resolved: seeds audits its own body of knowledge as `winnow` — all five flavors, edge-scoped detection"
status: resolved
type: question
created_at: 2026-06-15T21:58:55.152165+00:00
updated_at: 2026-09-01T17:18:38.252837+00:00
resolved_at: 2026-09-01T16:59:38.620530+00:00
tags:
  - self-audit
  - consistency
  - sanity-check
  - resolution-audit
  - corpus
  - meta
  - winnow
  - ratified
  - 2026-09-01
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
  - target_id: seeds-187
    rel_type: relates-to
    created_at: 2026-09-01T17:18:38.250786+00:00
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


---

## RESOLVED 2026-09-01 (Ryan). The command is `winnow`, and it covers all five flavors.

The umbrella question above — *formalize these as first-class tools, or leave them as things
an agent does on request?* — is answered **formalize**, and the generic form of that answer
was already settled independently in seeds-152.5: judgment becomes a skill, deterministic
work becomes a tested CLI verb. So `winnow` is a skill over a verb, the same shape as
`glean`.

### Name

`winnow` — separating what you keep from what you discard, out of material **already
harvested**. That scoping is the whole point of the name and it is what distinguishes this
from its sibling:

- **`glean`** (seeds-74.2.1) works the *field*: source transcripts in, new seeds out.
- **`winnow`** works the *barn*: the existing corpus in, attention out.

Adopting the Mar-2026 vocabulary from seeds-74.2.4, which was correct and was initially
mis-scoped as a stage of gleaning rather than an operation on the corpus. `thresh` remains
unused.

### Scope: all five flavors (Ryan's ruling)

Staleness, contradiction, outcome, learning, and neglected deferrals — the full family named
above, not a contradiction-only first cut. Ryan ruled this having heard the crying-wolf
objection, so the objection is answered by design rather than by narrowing scope:

1. **Hard and soft findings are reported separately.** Mechanical results (dates, graph
   state) are facts; staleness and outcome are guesses. Mixing them lets one soft false
   positive discredit the hard section.
2. **Every finding cites its evidence** — the specific seed IDs and the specific conflicting
   text. A finding that cannot cite is not reported.
3. **The split follows the flavor, not the feature.** Neglected deferrals and
   long-unresolved detection are pure graph-and-date facts and live in the verb, where
   pytest can cover them. Contradiction, staleness, outcome and learning need judgment and
   live in the skill — with the verb still scoping their candidate sets.
4. **The detector gets tested like a detector**, per the standing rule that a stale-check
   is itself code that can be silently wrong: hand-built fixtures with hand-computed
   answers, and critically a fixture pair that merely *looks* like a contradiction (two
   related seeds that agree) to prove the false-positive path.
5. **"Nothing to report" is a good outcome** and must never be padded with marginal
   findings to look productive.

### Detection — the thing that blocked this since June

seeds-164 is answered: **contradictions live inside clusters, not across the corpus.** The
candidate set is the edge set, not the cross product — 692 edges rather than ~49,000 pairs,
measured 2026-09-01. The unit of review is an *edge*, not a seed.

Evidence, produced by hand the same day: draining seeds-74.2 surfaced a real six-month-old
contradiction between seeds-74.2.1 and seeds-74.2.2 — two children of the same parent.

### Relationship to `doctor` and `check`

Now a clean three-way split, and worth stating so the boundaries hold:
- `seeds check` — are the FILES valid? (format rules)
- `seeds doctor` — is the STORE healthy? (operational: dangling edges, prefixes, counts)
- `seeds winnow` — is the THINKING healthy? (semantic: contradiction, staleness, neglect)
