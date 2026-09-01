---
id: seeds-52.1
title: "Review tagging: flag seeds for consultation with specific people or meetings"
status: resolved
type: idea
parent: seeds-52
created_at: 2026-02-06T16:29:40.234581+00:00
updated_at: 2026-02-06T16:34:43.693012+00:00
resolved_at: 2026-02-06T16:34:43.693004+00:00
tags:
  - workflow
  - model
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Context: Solo dev who occasionally needs to consult with a couple of people before implementing certain ideas. Not a team collaboration tool — just need a way to flag 'run this by Dave' or 'ask about this at the Thursday sync'. Share/assign model is overkill for this use case.

Key question: Can the existing tag system handle this, or do we need something more?


Resolution: Current tag system is sufficient. Use convention of double-tagging:
- A specific tag like `review:dave` or `review:thursday-sync` for the person/meeting
- A general `needs-review` tag for querying 'anything flagged for anyone'

No prefix/wildcard query needed. This keeps the tool simple and personal — solo dev who occasionally consults others, not a collaboration platform.
