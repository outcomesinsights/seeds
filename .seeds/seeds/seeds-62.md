---
id: seeds-62
title: "Idea: domain templates that scaffold seed structures"
status: captured
type: idea
created_at: 2026-02-05T21:43:13.399226+00:00
updated_at: 2026-02-24T17:04:48.159654+00:00
tags:
  - workflow
  - templates
  - future
relationships:
  - target_id: seeds-15
    rel_type: relates-to
    created_at: 2026-01-28T05:55:38.878483+00:00
  - target_id: seeds-61
    rel_type: relates-to
    created_at: 2026-02-05T21:43:08.458592+00:00
  - target_id: seeds-63
    rel_type: relates-to
    created_at: 2026-02-05T21:43:13.399226+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

From ETL feedback: some domains have known structures that could be templated.

For ETL, you could have a 'seeds etl init' that:
1. Takes a list of source tables
2. Creates a seed for each with the standard question 'include this table?'
3. Provides a checklist view of which decisions are made

This preserves ad-hoc exploration within the structure while ensuring completeness.

Other domains might have similar templates:
- Feature design (requirements → design → implementation → testing)
- Hiring decision (candidates → interview stages → offer)
- Architecture decision (options → evaluation criteria → selection)

Question: Is this seeds' job or a layer on top of seeds?


---
**Beads molecules/protos validate this idea (Feb 2026):**

Beads v0.50+ implemented this as "molecules" (work graphs) with a phase system:
- **Proto** (template): frozen, reusable scaffold
- **Mol** (instance): persistent active work from template
- **Wisp** (ephemeral): lightweight throwaway instance

Commands: `bd mol pour <proto>` (create from template), `bd mol squash` (compress to digest), `bd mol burn` (discard).

For seeds this could mean deliberation templates: "ADR evaluation" template scaffolds context → options → tradeoffs → decision. "Feature assessment" scaffolds requirements → constraints → alternatives → recommendation. The question "is this seeds' job or a layer on top?" — beads answered by making it a core feature.
