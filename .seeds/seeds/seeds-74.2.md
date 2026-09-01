---
id: seeds-74.2
title: "Resolved: capture is hybrid — cutting (proactive) + glean (retrospective)"
status: resolved
type: exploration
parent: seeds-74
created_at: 2026-02-06T22:02:47.824545+00:00
updated_at: 2026-09-01T16:58:33.624993+00:00
resolved_at: 2026-09-01T16:47:55.062265+00:00
tags:
  - workflow
  - meta
  - sweep
  - glean
  - cutting
  - resolved-2026-09-01
relationships:
  - target_id: seeds-78
    rel_type: questioned-by
    created_at: 2026-02-06T22:03:18.251599+00:00
  - target_id: seeds-79
    rel_type: questioned-by
    created_at: 2026-02-06T22:03:23.823335+00:00
  - target_id: seeds-x6m0
    rel_type: relates-to
    created_at: 2026-08-27T14:08:02.392709+00:00
  - target_id: seeds-h5rq
    rel_type: relates-to
    created_at: 2026-09-01T16:47:54.893918+00:00
  - target_id: seeds-159
    rel_type: relates-to
    created_at: 2026-09-01T16:58:33.623178+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

**Question:** Should seeds be captured during conversation (proactive) or extracted via post-conversation sweep (retrospective)?

**User's argument for sweep:**
- Holistic view of conversation reveals patterns: questions asked but not answered, decisions that led to other decisions/questions
- The conversation IS the context - sweep has full context available
- Trigger words or manual invocation ('sweep for seeds') could work
- Doesn't interrupt flow
- Proactive capture fails in practice - even with prime guidance, AI didn't stop to capture THIS conversation until told

**Key insight:** The failure mode of proactive capture was demonstrated in real-time. We discussed capture quality for 15+ minutes without making a seed about it.

**Sweep approach could identify:**
- Questions raised but not answered
- Questions answered that led to decisions
- Decisions that led to new questions
- Data discoveries with specific numbers/findings
- User clarifications/insights

**Open questions:**
- What triggers a sweep? End of session? Manual command? Keyword?
- How to present findings - auto-create seeds or suggest for user review?
- How to handle very long conversations?
- Could this work on historical conversations too?


---

## RESOLVED 2026-09-01. The question was a false binary; the answer is both, and both now have names.

**Ruling: hybrid.** Proactive capture during the conversation AND retrospective extraction
at the end. This was already decided in seeds-74.2.2 in March; what kept this cluster open
for six months was that the proactive half had no concrete shape, so there was nothing to
build and nothing to close.

Both halves are now specified:

| Half | Command | Seed |
|---|---|---|
| Proactive, in-conversation | `cutting` — capture a live topic with enough context to resume it cold | seeds-h5rq |
| Retrospective, end-of-session | `glean` — read the transcript, diff against the corpus, surface what was missed | seeds-74.2.1 |

Both are Claude Code skills. `cutting` is a pure skill (zero new CLI surface); `glean` is a
skill over a tested CLI verb. The split follows seeds-152.5 (deterministic -> verb,
judgment -> skill).

### The open questions, closed

- **What triggers it?** The skill's `description`, matched against user intent by the
  harness. Not a magic phrase, not a hook, not "land the plane".
- **Auto-create or suggest?** Suggest-and-review by default; `--auto` kept as an opt-in for
  bulk historical passes, with the audit guardrail recorded in seeds-74.2.1.
- **Very long conversations?** Dissolved. The verb filters to a candidate list, so the model
  never receives the raw transcript. (Measured: an ordinary session is 502KB / 256 turns.)
- **Historical conversations?** Yes — that is what `--auto` and `--since` exist for, with
  gleaned conversations tracked so re-gleaning is deliberate rather than accidental.

### What the delay cost, worth recording

Two of this seed's children contradicted each other for roughly six months —
seeds-74.2.2 concluded "analyse the model's context", seeds-74.2.1 later proved that cannot
work after compaction — and neither was reconciled because nothing forced a pass over the
cluster. The "proactive capture fails in practice" insight at the top of this seed turns
out to apply to *deliberation* as much as to capture: an unresolved cluster decays the same
way an uncaptured tangent does.

This is the strongest available argument for `glean` existing at all, and it is why the
cluster was drained before either command was built rather than after.
