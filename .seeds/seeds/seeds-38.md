---
id: seeds-38
title: Do LLMs retrieve/update structured data (JSON) better than semi-structured (markdown)?
status: resolved
type: question
created_at: 2026-01-28T20:02:20.838289+00:00
updated_at: 2026-01-28T20:02:20.838289+00:00
resolved_at: 2026-01-28T20:06:31.934835+00:00
relationships:
  - target_id: seeds-1
    rel_type: questions
    created_at: 2026-01-28T20:02:20.838289+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

No universal winner - depends on use case. YAML performed best for nested data (54% more correct in some tests). Markdown is token-efficient and chunks cleanly. JSON brackets break awkwardly when chunked. JSON better for precise lookups; Markdown/YAML better for RAG. For seeds: markdown-style structure likely better since JSON is fragile when partially retrieved.
