---
id: seeds-ryfk
title: Should the inside-out reviewer call 'seeds winnow --flavor contradiction' scoped to the seed set instead of re-deriving contradictions by reading? Winnow already walks the edge graph deterministically, but it only compares seeds that are ALREADY LINKED — and an unnoticed contradiction inside one session's output is exactly the case where nobody drew the edge.
status: resolved
type: question
created_at: 2026-09-16T14:52:43.173023+00:00
updated_at: 2026-09-16T16:07:39.041441+00:00
resolved_at: 2026-09-16T16:07:39.041432+00:00
relationships:
  - target_id: seeds-cpkr
    rel_type: questions
    created_at: 2026-09-16T14:52:43.175112+00:00
---

Yes — and as a general rule, not just for this lens: scrutinize composes the verbs seeds already has instead of re-deriving their work by reading. Contradiction and staleness within the seed set come from 'seeds winnow' scoped to those seeds; the capture gap comes from 'seeds glean' upstream.

Necessary, not sufficient. Winnow's contradiction flavor walks the relationship graph, so it only compares seeds ALREADY LINKED — and a contradiction inside one session's output is the case where nobody drew the edge. So the tool removes the burden of finding contradictions among linked seeds, and the inside-out reviewer still has to read for the unlinked ones. Composing it narrows the read; it does not replace it.

REVISED 2026-09-16, after the adversarial review measured it. The principle stands; the winnow half does not.

Keep glean. Drop winnow. Two independent findings killed it:

1. It is not executable as ruled. 'seeds winnow' takes --flavor, --since and --json and nothing else (src/seeds/cli.py:2294-2358); it calls winnow(store.all(), ...) unconditionally. There is no --seeds, no --scope, no ID filter. The ruling specified a capability that does not exist, and 'a skill with no verb' forbids adding one.

2. Even scoped, it returns nothing at the moment it was designed for. Every gate is an age gate or a resolved-status gate: NEGLECT_DAYS = 90, UNRESOLVED_DAYS = 180, STALE_DAYS = 180 (winnow.py:89-96); contradiction requires both endpoints RESOLVED; staleness requires resolved_at older than the cutoff. A deliberation that converged yesterday satisfies none of them. Run live over the whole corpus: one candidate, and it is a false positive (a question linked to its own answer).

And the residue this answer originally accepted -- 'the reviewer still has to read for the unlinked ones' -- is explicitly banned by the winnow skill, on measured evidence: 'Do not go hunting the corpus for what it missed... the looser rule that caught the pair produced 5 false positives out of 7, including seeds that plainly agreed. If you think the rule has a systematic gap, file a seed about the rule. Do not widen it by hand inside a report.' The two skills collided and the deliberation never noticed.

So: compose glean, which works and is load-bearing. Do not compose winnow. And scrutinize READS .seeds/gleaned.jsonl to check that someone gleaned -- it must never RUN glean, because mark_gleaned fires unconditionally (cli.py:2269) and a later real pass then prints 'was gleaned ... pass --force' and files nothing. Running it would destroy the capture the whole design is ordered around.
