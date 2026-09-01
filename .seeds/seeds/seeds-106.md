---
id: seeds-106
title: Should we generate hosted API docs (Sphinx/mkdocs) for beta?
status: resolved
type: question
created_at: 2026-02-27T15:21:15.850770+00:00
updated_at: 2026-02-27T15:21:15.850770+00:00
resolved_at: 2026-02-27T15:21:23.738336+00:00
relationships:
  - target_id: seeds-93
    rel_type: questions
    created_at: 2026-02-27T15:21:15.850770+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

No hosted docs for beta. Add thorough docstrings to all modules/functions during the type-checking pass. Docstrings + CLI --help is the API surface. Hosted docs can be layered on later.
