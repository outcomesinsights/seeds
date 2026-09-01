---
id: seeds-74.1
title: Improve seed capture quality at creation time
status: resolved
type: exploration
parent: seeds-74
created_at: 2026-02-06T21:34:36.003896+00:00
updated_at: 2026-02-06T21:54:25.425505+00:00
resolved_at: 2026-02-06T21:54:25.425496+00:00
tags:
  - workflow
  - ux
relationships:
  - target_id: seeds-76
    rel_type: questioned-by
    created_at: 2026-02-06T21:34:48.183665+00:00
  - target_id: seeds-77
    rel_type: questioned-by
    created_at: 2026-02-06T21:47:13.047289+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Focus: Seeds often lack sufficient detail when created. How to improve capture quality?

**Potential approaches:**
- Structured prompts during creation (why, alternatives, context)
- Templates for different seed types (decision vs idea vs concern)
- AI-assisted expansion: take a jot and prompt for elaboration
- Review step before finalizing a seed

**Tension:**
- jot is intentionally low-friction for quick capture
- But quick capture = thin content
- Maybe a two-phase flow: jot fast, enrich later?



## Analysis: blargyblarg WIDGETTYP case study

Compared conversations in ~/.claude/projects/ to seeds in superduperdata_blargyblarg.

**What conversations captured but seeds missed:**
1. Actual DuckDB queries run to verify data
2. Step-by-step discovery (checking each table, finding NULL correlation)
3. User insight: 'WIDGETTYP governs which generator, not a mapped value'
4. Formatted data tables with exact counts per table
5. Later iterations/refinements from TODO reviews

**What seeds DID capture:**
- Final decisions and conclusions
- Vocabulary mappings
- Generator WHERE clauses

**Gap:** ~240 conversation lines about widgettyp → ~10 seeds with conclusions only. Investigation and reasoning lost.
