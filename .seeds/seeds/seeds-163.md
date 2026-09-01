---
id: seeds-163
title: Do we formalize these self-audit checks as first-class seeds commands (a seeds audit / seeds check family), or leave them as things an agent does on request?
status: resolved
type: question
created_at: 2026-06-15T22:00:38.897417+00:00
updated_at: 2026-09-01T16:59:21.151759+00:00
resolved_at: 2026-09-01T16:59:21.151750+00:00
relationships:
  - target_id: seeds-158
    rel_type: questions
    created_at: 2026-06-15T22:00:38.902502+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

**Answered 2026-09-01 (Ryan): formalize — as `winnow`, a skill over a tested CLI verb.**

The generic form of this question was settled independently in seeds-152.5, ratified the
same day: **deterministic work becomes a tested CLI verb; judgment stays a thin skill.** So
this is not an either/or between "first-class command" and "thing an agent does on request"
— it is both, layered, and the layer boundary follows the flavor rather than the feature:

- **Verb (`seeds winnow`)** — neglected deferrals and long-unresolved detection (pure
  status/date/graph facts, see seeds-162), plus candidate *scoping* for the judgment
  flavors: emit the edge pairs worth comparing, emit resolved seeds citing checkable
  premises. All of it pytest-covered.
- **Skill** — the judgment: is this pair actually contradictory, has this premise actually
  aged out, is this worth the user's attention.

Rejected: leaving it entirely ad hoc. The corpus supplies the counter-evidence — the
contradiction between seeds-74.2.1 and seeds-74.2.2 sat unreconciled for roughly six months
precisely because nothing but an unprompted agent decision would have caught it, and no such
decision ever happened. "An agent could do this on request" is true and insufficient; the
whole failure mode is that nobody makes the request.

Also rejected: naming it a `seeds audit` / `seeds check` family. `seeds check` already means
something narrower and specific (are the files valid?), and overloading it would blur a
boundary that is currently clean:

- `seeds check` — are the FILES valid? (format rules)
- `seeds doctor` — is the STORE healthy? (operational)
- `seeds winnow` — is the THINKING healthy? (semantic)
