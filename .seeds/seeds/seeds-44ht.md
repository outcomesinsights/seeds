---
id: seeds-44ht
title: What problem is this actually solving — JSONL merge conflicts across hosts, or wanting a versioned history of how a seed's thinking evolved? The answer picks the solution, and only one of them needs Dolt.
status: resolved
type: question
created_at: 2026-08-26T03:35:18.041900+00:00
updated_at: 2026-08-26T03:39:21.777525+00:00
resolved_at: 2026-08-26T03:39:21.777518+00:00
relationships:
  - target_id: seeds-lcfa
    rel_type: questions
    created_at: 2026-08-26T03:35:18.045001+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Data-level merge, plus the wiring around it. Concretely: seeds are edited on separate hosts, hooks dump the DB to JSONL, and then someone has to REMEMBER to pull the JSONL back into the local DB. It feels rickety.
