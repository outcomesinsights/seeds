---
id: seeds-bwce
title: "Class B: does the writer chase prettier's escape-minimizing quote choice (emit single-quoted when the value contains a double quote and needs no other escape, and teach the reader that second form), or does the format hold one quoting spelling and accept that 10 corpus files hard-fail under a default prettier run?"
status: resolved
type: question
created_at: 2026-09-08T21:02:27.747503+00:00
updated_at: 2026-09-08T21:14:11.378751+00:00
resolved_at: 2026-09-08T21:14:11.378742+00:00
relationships:
  - target_id: seeds-dv6r.1
    rel_type: questions
    created_at: 2026-09-08T21:02:27.748556+00:00
---

Chase it — ruled by @aguynamedryan 2026-09-08. The writer emits the single-quoted form when the value contains a double quote and needs no other escape; the reader learns that second spelling. Verified: with this plus the ---\n separator change, 0 of 1,324 corpus files change in frontmatter or separator under prettier --write.
