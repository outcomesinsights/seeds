---
id: seeds-37
title: Do LLMs interrelate many small chunks better, or process one large coherent chunk better?
status: resolved
type: question
created_at: 2026-01-28T20:02:20.356727+00:00
updated_at: 2026-01-28T20:02:20.356727+00:00
resolved_at: 2026-01-28T20:06:31.424531+00:00
relationships:
  - target_id: seeds-1
    rel_type: questions
    created_at: 2026-01-28T20:02:20.356727+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Research favors moderate-sized focused chunks over large documents. 'Lost in the Middle' effect (Liu et al., Stanford) shows LLMs have 20%+ accuracy drops for information buried in middle of long contexts. Optimal chunk size: 500-1800 chars. Chunking strategy matters more than model quality. Implication: smaller focused seeds better than large monolithic ones.
