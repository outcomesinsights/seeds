---
id: seeds-52
title: Need way to flag seeds as waiting-on-person
status: resolved
type: idea
created_at: 2026-02-05T19:35:12.212453+00:00
updated_at: 2026-02-06T16:34:49.303199+00:00
resolved_at: 2026-02-06T16:34:49.303191+00:00
tags:
  - workflow
  - model
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Emerged from real usage: often need to flag a decision as blocked pending input from a specific person (e.g., 'waiting on Alice for data schema'). Current workarounds (defer with note, tags like waiting:alice, attached questions) don't support querying 'show me everything waiting on Alice'. Possible approaches: 1) blocked_by field that can reference people/external entities 2) Special tag convention with query support 3) New status like 'waiting' with assignee field


Resolution: Tag conventions handle the 'waiting on person' use case well enough. Use double-tagging: specific tag (e.g. review:dave) plus general tag (needs-review). No model changes needed — the existing tag system with LIKE queries supports exact tag filtering, and the double-tag convention covers the 'show me everything needing review' case.
