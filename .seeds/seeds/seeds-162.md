---
id: seeds-162
title: Are deferred seeds falling through the cracks — should seeds surface neglected deferrals that have gone quiet?
status: resolved
type: question
created_at: 2026-06-15T22:00:38.773077+00:00
updated_at: 2026-09-01T16:59:21.289169+00:00
resolved_at: 2026-09-01T16:59:21.289161+00:00
relationships:
  - target_id: seeds-158
    rel_type: questions
    created_at: 2026-06-15T22:00:38.777316+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

**Answered 2026-09-01: yes — and it is the cheapest of `winnow`'s five flavors.**

Neglected deferrals are one of the five flavors Ryan ruled into scope for `winnow`
(seeds-158). They are also the flavor that needs no judgment at all: "deferred, and nothing
has touched it since <date>" is a pure function of status, timestamps and graph position,
alongside its sibling case "blocked, but every blocker is now closed."

That makes it **verb work, not skill work** (seeds-152.5): deterministic, pytest-coverable,
and a hard finding rather than a guess.

This matters beyond the flavor itself. `winnow` reports hard findings separately from soft
ones precisely so a speculative staleness guess cannot discredit the section of the report
that is simply factual — and neglected deferrals are the anchor of that hard section.

Live evidence that the answer is yes: seeds-159 has been `deferred` since June 2026 while
the question blocking it (seeds-164) turned out to be answerable from a case that arose in
ordinary work. Nothing surfaced it. It was found today only because a human went looking
for something adjacent.
