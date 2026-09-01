---
id: seeds-3uir
title: An import record carries an unrecognized seed_type. What happens to that record, and to the rest of the file?
status: resolved
type: question
created_at: 2026-08-28T13:06:03.704873+00:00
updated_at: 2026-08-31T20:02:46.789802+00:00
resolved_at: 2026-08-28T13:28:26.772863+00:00
relationships:
  - target_id: seeds-1x6b
    rel_type: questions
    created_at: 2026-08-28T13:06:03.709179+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Nothing — the premise was wrong. The vocabulary opens up fully: seed_type becomes a free string at every layer, including `--type` on create. Only 'question' carries behavior (seeds ask/answer, seeds questions, prime, web); the other four have zero branches in the codebase, so the enum was enforcing a suggestion at the two boundaries where enforcement is most dangerous — stored data and the cross-version sync format — while Click already caught typos at the one place humans make them. @markdanese's 'context' seeds become ordinary data and the outage never happens. @aguynamedryan chose fully open over keeping --type constrained, accepting that a typo silently becomes a new category; doctor's vocabulary listing is the visibility mechanism instead.
