---
id: seeds-10
title: "JSONL export format: nested vs referenced structure"
status: captured
type: question
created_at: 2026-01-28T05:54:11.304384+00:00
updated_at: 2026-01-28T05:55:25.973243+00:00
tags:
  - storage
  - export
converted_at: 2026-09-01T05:20:22.746832+00:00
---

From discussion.md: 'With the more complicated and granular the set of models, the more difficult it might be for us to export those bits of information into JSONL files like beads does.'

Questions:
- Do nested seeds get embedded in their parent's JSONL line?
- Or do they have their own lines with references to parent IDs?
- Are IDs inferred from hierarchy (e.g., seed-a1b2.1.2)?

Should investigate: How does Beads handle sub-issues in JSONL export?

From mvp.md: Current design uses one seed per line, questions embedded:
{"id": "seed-a1b2", ..., "questions": [{...}]}
