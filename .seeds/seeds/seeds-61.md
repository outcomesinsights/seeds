---
id: seeds-61
title: "ETL workflow pattern: hierarchical seed structure"
status: captured
type: exploration
created_at: 2026-02-05T21:43:08.458592+00:00
updated_at: 2026-02-06T00:09:44.623939+00:00
tags:
  - workflow
  - etl
  - feedback
relationships:
  - target_id: seeds-60
    rel_type: relates-to
    created_at: 2026-02-05T21:43:03.052122+00:00
  - target_id: seeds-62
    rel_type: relates-to
    created_at: 2026-02-05T21:43:08.458592+00:00
  - target_id: seeds-63
    rel_type: relates-to
    created_at: 2026-02-05T21:43:08.458592+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Observed pattern from ETL design work:

**Level 1: Source Tables**
- One seed per source table
- Question: 'Will we include table X?'
- Answer: yes/no with rationale

**Level 2: Generators (if table included)**
- Question: 'What target tables will source X generate?'
- Creates child seeds for each generator

**Level 3: Generator Details**
- Each generator becomes a seed
- Flesh out column mappings

**Level 4: Individual Mappings (maybe)**
- Each mapping could be a seed
- But this might explode into too many seeds

**Tension:** Granularity vs manageability. At what level do seeds become too numerous to be useful?

**Possible approaches:**
1. Templates/wizards that create seed hierarchies for known domains
2. Bulk seed creation from structured input (CSV of table names?)
3. Different tools for different granularity (seeds for decisions, spreadsheet for mappings?)
