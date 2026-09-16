---
id: seeds-ryfk
title: Should the inside-out reviewer call 'seeds winnow --flavor contradiction' scoped to the seed set instead of re-deriving contradictions by reading? Winnow already walks the edge graph deterministically, but it only compares seeds that are ALREADY LINKED — and an unnoticed contradiction inside one session's output is exactly the case where nobody drew the edge.
status: resolved
type: question
created_at: 2026-09-16T14:52:43.173023+00:00
updated_at: 2026-09-16T15:05:48.248945+00:00
resolved_at: 2026-09-16T15:05:48.248935+00:00
relationships:
  - target_id: seeds-cpkr
    rel_type: questions
    created_at: 2026-09-16T14:52:43.175112+00:00
---

Yes — and as a general rule, not just for this lens: scrutinize composes the verbs seeds already has instead of re-deriving their work by reading. Contradiction and staleness within the seed set come from 'seeds winnow' scoped to those seeds; the capture gap comes from 'seeds glean' upstream.

Necessary, not sufficient. Winnow's contradiction flavor walks the relationship graph, so it only compares seeds ALREADY LINKED — and a contradiction inside one session's output is the case where nobody drew the edge. So the tool removes the burden of finding contradictions among linked seeds, and the inside-out reviewer still has to read for the unlinked ones. Composing it narrows the read; it does not replace it.
