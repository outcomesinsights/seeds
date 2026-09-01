---
id: seeds-tct2
title: Should 'seeds doctor' compare JSONL content against the DB (not mtime), and exit non-zero when they diverge?
status: resolved
type: question
created_at: 2026-08-28T13:06:03.823559+00:00
updated_at: 2026-08-28T13:28:26.898947+00:00
resolved_at: 2026-08-28T13:28:26.898938+00:00
relationships:
  - target_id: seeds-1x6b
    rel_type: questions
    created_at: 2026-08-28T13:06:03.826598+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Yes to both. doctor compares JSONL record IDs against the DB, names what each side is missing, and exits non-zero on divergence — making it a real gate suitable for a pre-commit or CI hook. The mtime comparison goes away: it is not merely a weak proxy but one that certifies exactly the state a failed import produces.
