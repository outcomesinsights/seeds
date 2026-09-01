---
id: seeds-02ur
title: "Cleanup: 36 orphaned legacy rows in the questions table, unreferenced since the v2 question-seeds migration"
status: captured
type: idea
created_at: 2026-08-26T04:02:54.250253+00:00
updated_at: 2026-08-31T21:41:37.323343+00:00
tags:
  - cleanup
  - schema
  - legacy
  - migration
  - questions
  - 2026-08-25
relationships:
  - target_id: seeds-lcfa.6
    rel_type: relates-to
    created_at: 2026-08-26T04:03:23.872421+00:00
  - target_id: seeds-sdhc.1
    rel_type: relates-to
    created_at: 2026-08-31T20:05:41.629958+00:00
  - target_id: seeds-tz66
    rel_type: relates-to
    created_at: 2026-08-31T22:21:03.059935+00:00
  - target_id: seeds-not2
    rel_type: relates-to
    created_at: 2026-09-01T00:49:49.413635+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Found incidentally while inspecting the schema during the storage deliberation (seeds-lcfa.6), 2026-08-25. Small, concrete, and safe — recorded so it does not get rediscovered a third time.

WHAT IS THERE. `.seeds/seeds.db` still has a `questions` table holding 36 rows, ids in the legacy `q-XXXX` form, pointing at parent seeds in the legacy `seed-XXXX` form (seed-0fb1, seed-1f89, seed-4653, seed-4653.1). Created between 2026-01-28 and 2026-03-11. Neither id form appears anywhere in `.seeds/seeds.jsonl`.

IT IS NOT DATA LOSS — checked before raising it. Sampling three of the rows and grepping their text against the tracked JSONL found all three present: the question CONTENT was migrated into first-class question-seeds under the v2 format, which is why `seeds ask` today produces a normal seed id (seeds-44ht, for instance) rather than a `q-` id. What remains in the table is the pre-migration representation, orphaned.

WHY IT IS WORTH DOING ANYWAY:
- It is a trap for the next person reading the schema. The obvious inference from "36 rows in `questions`, zero `q-` ids in the JSONL" is that questions are silently not being exported — which is alarming, wrong, and costs someone an hour to disprove. It cost one today.
- export.py still carries the v1 import path for embedded questions (around export.py:417-447, converting embedded questions to question-seeds plus relationships). Whether that stays is a separate call — it is the migration path for old data from elsewhere — but the TABLE it fed is dead.
- Any storage rework (per-seed files, or an engine change) has to decide what to do with this table anyway. Better to delete it deliberately now than to port dead rows into a new format.

BEFORE DELETING: confirm no code path still reads the `questions` table, and confirm the v1 importer does not need it as a landing zone for old exports it might still encounter. If the v1 path does need a target, it should write question-seeds directly rather than into the legacy table.

SCHEDULED (2026-08-31): the converter drops the table rather than translating it. Re-measured today — all 36 of 36 rows are orphaned, so the table is entirely debris, not partially. Also worth recording: 'seeds doctor' reports "549 relationships, no orphans" while this table sits 100% orphaned, because the orphan check never looks at it. That is a live detection gap and an argument for the plausibility tier in seeds-sdhc.2.
