---
id: seeds-142
title: "Transcript-incorporation workflow: dedupe-and-create against existing seeds (recurring use case)"
status: captured
type: exploration
created_at: 2026-05-18T15:57:25.771304+00:00
updated_at: 2026-05-18T15:57:25.771315+00:00
tags:
  - workflow
  - ai-ux
  - transcript
  - gleaning
  - incorporate
  - recurring
relationships:
  - target_id: seeds-87
    rel_type: relates-to
    created_at: 2026-05-18T15:58:19.686055+00:00
  - target_id: seeds-130
    rel_type: relates-to
    created_at: 2026-05-18T15:58:19.771910+00:00
  - target_id: seeds-74.2.1
    rel_type: relates-to
    created_at: 2026-05-18T15:58:19.859270+00:00
  - target_id: seeds-2
    rel_type: relates-to
    created_at: 2026-05-18T15:58:19.942995+00:00
  - target_id: seeds-143
    rel_type: relates-to
    created_at: 2026-05-18T16:44:28.805862+00:00
  - target_id: seeds-112.4
    rel_type: relates-to
    created_at: 2026-06-05T17:26:20.473018+00:00
  - target_id: seeds-181
    rel_type: relates-to
    created_at: 2026-06-23T20:44:22.434941+00:00
  - target_id: seeds-181.1
    rel_type: relates-to
    created_at: 2026-06-23T20:44:23.068605+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

**Use case observed in production (2026-04 to 2026-05):**

User points Claude at an extracted-transcript file ('look over these and update existing seeds or create new ones'). Claude must:
1. Identify candidate items in the transcript (questions, decisions, data, insights)
2. For each, decide: existing seed? update which one? net-new?
3. Write seeds with correct cross-references and links

**Empirical observations (from Clancey conversation review):**
- Recurring: 6+ sessions in 3 weeks (4/23, 5/4, 5/6, 5/8, 5/12, 5/15 on CSC; 5/8 on oimnibus)
- Discovery pattern varies wildly across sessions: `seeds list`, `seeds search`, `cat .seeds/seeds.jsonl | grep`, multi-read `seeds show`. No canonical pattern.
- Failure mode: hallucinated seed IDs in newly-written bodies (4/23 catalog, 5/8 oimnibus both had self-corrections of crossed references)
- User ask: 'focus only on dates I haven't read' — currently Claude derives this from updated_at timestamps inside seed bodies, no CLI primitive answers it
- Gold-standard pattern (5/6 subagents): list → targeted search → read 4-6 neighbors → check candidate doc for duplicates → then write

**Related existing infrastructure:**
- A `transcript-seeds` skill already wraps this workflow as a slash command — validates the design need
- seeds-130 covers the project-aware-gleaning meta-problem
- seeds-87 covers part of the cold-start cost (dynamic prime)
- seeds-74.2.1 (sweep) is a sibling pattern for conversation extraction

**Missing primitives motivated by this use case (see child seeds):**
- A digest in `seeds prime` so Claude doesn't restart discovery each session — see seeds-87 evidence update
- A `seeds suggest <text>` dedup query (FTS5 + tag-overlap ranking)
- A `seeds recent --since=<date>` view for incremental ingestion
- ID-reference validation on create/update to catch hallucinated cross-refs

**Why first-class:** Not a one-off. Six instances in three weeks across two projects. Worth optimizing the primitives instead of patching the workflow each time.
